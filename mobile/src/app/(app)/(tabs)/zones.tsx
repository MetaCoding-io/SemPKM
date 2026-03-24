/**
 * Zone management screen with map and zone list.
 *
 * Top section: MapView showing zone circles and user location.
 * Bottom section: FlatList with zone items (name, radius badge,
 * enable/disable switch, delete button).
 *
 * Zone CRUD flows through the backend API via SemPKMClient.
 * After any mutation, geofence registrations are synced via
 * registerGeofences() from the geofencing service.
 *
 * @module app/(app)/(tabs)/zones
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import MapView, { Circle, LongPressEvent, Marker, Region } from 'react-native-maps';
import Ionicons from '@expo/vector-icons/Ionicons';

import { useSession, parseSession } from '@/ctx';
import { SemPKMClient, SemPKMError } from '@/api/client';
import type { Zone } from '@/api/client';
import { registerGeofences } from '@/services/geofencing';
import { requestLocationPermissions } from '@/services/permissions';
import ZoneEditor from '@/components/ZoneEditor';
import type { ZoneEditorData } from '@/components/ZoneEditor';

// ── Constants ───────────────────────────────────────────────────

/** iOS has a hard limit of ~20 monitored regions. Warn near it. */
const IOS_ZONE_WARNING_THRESHOLD = 15;
const IOS_ZONE_HARD_LIMIT = 20;

/** Default map region (roughly center of US — will re-center on zones). */
const DEFAULT_REGION: Region = {
  latitude: 39.8283,
  longitude: -98.5795,
  latitudeDelta: 30,
  longitudeDelta: 30,
};

// ── Component ───────────────────────────────────────────────────

export default function ZonesScreen() {
  const { session } = useSession();
  const mapRef = useRef<MapView>(null);

  // ── State ─────────────────────────────────────────────────────

  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Editor modal state
  const [editorVisible, setEditorVisible] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | undefined>(undefined);
  const [newCenter, setNewCenter] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);

  // Track whether permissions have been requested this session
  const [permissionsRequested, setPermissionsRequested] = useState(false);

  // ── API client helper ─────────────────────────────────────────

  const getClient = useCallback((): SemPKMClient | null => {
    const creds = parseSession(session);
    if (!creds) return null;
    return new SemPKMClient(creds.instanceUrl, creds.apiKey);
  }, [session]);

  // ── Fetch zones ───────────────────────────────────────────────

  const fetchZones = useCallback(
    async (isRefresh = false) => {
      const client = getClient();
      if (!client) return;

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const result = await client.getZones();
        setZones(result);
      } catch (err) {
        if (err instanceof SemPKMError) {
          setError(
            err.status === 0
              ? 'Could not reach server. Check your connection.'
              : `Server error: ${err.detail ?? err.message}`,
          );
        } else {
          setError('An unexpected error occurred.');
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [getClient],
  );

  useEffect(() => {
    fetchZones();
  }, [fetchZones]);

  // ── Geofence sync helper ──────────────────────────────────────

  const syncGeofences = useCallback(async (updatedZones: Zone[]) => {
    try {
      const enabled = updatedZones
        .filter((z) => z.enabled)
        .map((z) => ({
          name: z.name,
          latitude: z.latitude,
          longitude: z.longitude,
          radius_meters: z.radius_meters,
          enabled: true as const,
        }));
      await registerGeofences(enabled);
    } catch (err) {
      console.warn('zones.geofence_sync_failed', err);
    }
  }, []);

  // ── Permission request (once per session, on first zone create) ─

  const ensurePermissions = useCallback(async () => {
    if (permissionsRequested) return;
    setPermissionsRequested(true);

    const status = await requestLocationPermissions();
    if (status.background !== 'granted') {
      Alert.alert(
        'Background Location',
        'Geofencing requires "Always" location access to work when the app is closed. ' +
          "Zones will still be saved, but geofence triggers won't fire in the background.",
        [{ text: 'OK' }],
      );
    }
  }, [permissionsRequested]);

  // ── Map press → new zone ──────────────────────────────────────

  const handleMapLongPress = (e: LongPressEvent) => {
    const { latitude, longitude } = e.nativeEvent.coordinate;
    setNewCenter({ latitude, longitude });
    setEditingZone(undefined);
    setEditorVisible(true);
  };

  // ── Open editor for create ────────────────────────────────────

  const openCreateEditor = () => {
    setEditingZone(undefined);
    setNewCenter(null);
    setEditorVisible(true);
  };

  // ── Open editor for edit ──────────────────────────────────────

  const openEditEditor = (zone: Zone) => {
    setEditingZone(zone);
    setNewCenter({ latitude: zone.latitude, longitude: zone.longitude });
    setEditorVisible(true);
  };

  // ── Save zone (create or update) ──────────────────────────────

  const handleSave = async (data: ZoneEditorData) => {
    const client = getClient();
    if (!client) return;

    setEditorVisible(false);

    try {
      let updatedZones: Zone[];

      if (editingZone) {
        // Update existing zone
        const updated = await client.updateZone(editingZone.id, {
          name: data.name,
          latitude: data.latitude,
          longitude: data.longitude,
          radius_meters: data.radius_meters,
        });
        updatedZones = zones.map((z) => (z.id === updated.id ? updated : z));
      } else {
        // Create new zone — request permissions on first ever create
        if (zones.length === 0) {
          await ensurePermissions();
        }

        const created = await client.createZone({
          name: data.name,
          latitude: data.latitude,
          longitude: data.longitude,
          radius_meters: data.radius_meters,
          enabled: true,
        });
        updatedZones = [...zones, created];
      }

      setZones(updatedZones);
      await syncGeofences(updatedZones);
    } catch (err) {
      const msg =
        err instanceof SemPKMError
          ? err.detail ?? err.message
          : 'Failed to save zone.';
      Alert.alert('Error', msg);
    }

    setEditingZone(undefined);
    setNewCenter(null);
  };

  // ── Toggle zone enabled ───────────────────────────────────────

  const handleToggle = async (zone: Zone) => {
    const client = getClient();
    if (!client) return;

    try {
      const updated = await client.updateZone(zone.id, {
        enabled: !zone.enabled,
      });
      const updatedZones = zones.map((z) => (z.id === updated.id ? updated : z));
      setZones(updatedZones);
      await syncGeofences(updatedZones);
    } catch (err) {
      const msg =
        err instanceof SemPKMError
          ? err.detail ?? err.message
          : 'Failed to update zone.';
      Alert.alert('Error', msg);
    }
  };

  // ── Delete zone ───────────────────────────────────────────────

  const handleDelete = (zone: Zone) => {
    Alert.alert(
      'Delete Zone',
      `Delete "${zone.name}"? This cannot be undone.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            const client = getClient();
            if (!client) return;

            try {
              await client.deleteZone(zone.id);
              const updatedZones = zones.filter((z) => z.id !== zone.id);
              setZones(updatedZones);
              await syncGeofences(updatedZones);
            } catch (err) {
              const msg =
                err instanceof SemPKMError
                  ? err.detail ?? err.message
                  : 'Failed to delete zone.';
              Alert.alert('Error', msg);
            }
          },
        },
      ],
    );
  };

  // ── Center map on zone ────────────────────────────────────────

  const centerOnZone = (zone: Zone) => {
    mapRef.current?.animateToRegion(
      {
        latitude: zone.latitude,
        longitude: zone.longitude,
        // Scale delta to roughly 3× the zone radius in degrees
        latitudeDelta: (zone.radius_meters / 111_320) * 6,
        longitudeDelta: (zone.radius_meters / 111_320) * 6,
      },
      500,
    );
  };

  // ── Loading state ─────────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  // ── Error state ───────────────────────────────────────────────

  if (error && zones.length === 0) {
    return (
      <View style={styles.centered}>
        <Ionicons name="cloud-offline-outline" size={48} color="#9ca3af" />
        <Text style={styles.errorText}>{error}</Text>
        <Pressable style={styles.retryButton} onPress={() => fetchZones()}>
          <Text style={styles.retryBtnText}>Retry</Text>
        </Pressable>
      </View>
    );
  }

  // ── Compute initial region from zones ─────────────────────────

  const initialRegion =
    zones.length > 0
      ? {
          latitude: zones[0].latitude,
          longitude: zones[0].longitude,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        }
      : DEFAULT_REGION;

  const enabledCount = zones.filter((z) => z.enabled).length;

  // ── Render ────────────────────────────────────────────────────

  return (
    <View style={styles.container}>
      {/* Map section */}
      <View style={styles.mapContainer}>
        <MapView
          ref={mapRef}
          style={styles.map}
          initialRegion={initialRegion}
          showsUserLocation
          showsMyLocationButton
          onLongPress={handleMapLongPress}
        >
          {zones.map((zone) => (
            <React.Fragment key={zone.id}>
              <Circle
                center={{
                  latitude: zone.latitude,
                  longitude: zone.longitude,
                }}
                radius={zone.radius_meters}
                fillColor={
                  zone.enabled
                    ? 'rgba(37, 99, 235, 0.15)'
                    : 'rgba(156, 163, 175, 0.1)'
                }
                strokeColor={zone.enabled ? '#2563eb' : '#9ca3af'}
                strokeWidth={2}
              />
              <Marker
                coordinate={{
                  latitude: zone.latitude,
                  longitude: zone.longitude,
                }}
                title={zone.name}
                description={`${zone.radius_meters}m radius${zone.enabled ? '' : ' (disabled)'}`}
              />
            </React.Fragment>
          ))}
        </MapView>

        {/* Zone count + warning */}
        {zones.length > 0 && (
          <View style={styles.zoneCountBadge}>
            <Text style={styles.zoneCountText}>
              {enabledCount}/{zones.length} active
            </Text>
          </View>
        )}

        {enabledCount >= IOS_ZONE_WARNING_THRESHOLD && (
          <View style={styles.warningBadge}>
            <Ionicons name="warning-outline" size={14} color="#d97706" />
            <Text style={styles.warningText}>
              {enabledCount}/{IOS_ZONE_HARD_LIMIT} iOS region limit
            </Text>
          </View>
        )}
      </View>

      {/* Zone list section */}
      {zones.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="location-outline" size={40} color="#9ca3af" />
          <Text style={styles.emptyTitle}>No zones configured</Text>
          <Text style={styles.emptySubtext}>
            Tap + to add your first zone, or long-press the map.
          </Text>
        </View>
      ) : (
        <FlatList
          data={zones}
          keyExtractor={(item) => item.id}
          style={styles.list}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => fetchZones(true)}
            />
          }
          renderItem={({ item }) => (
            <ZoneListItem
              zone={item}
              onPress={() => centerOnZone(item)}
              onEdit={() => openEditEditor(item)}
              onToggle={() => handleToggle(item)}
              onDelete={() => handleDelete(item)}
            />
          )}
          ListFooterComponent={
            error ? (
              <Text style={styles.inlineError}>{error}</Text>
            ) : null
          }
        />
      )}

      {/* Floating action button */}
      <Pressable style={styles.fab} onPress={openCreateEditor}>
        <Ionicons name="add" size={28} color="#fff" />
      </Pressable>

      {/* Editor modal */}
      <ZoneEditor
        visible={editorVisible}
        zone={editingZone}
        center={newCenter}
        onSave={handleSave}
        onCancel={() => {
          setEditorVisible(false);
          setEditingZone(undefined);
          setNewCenter(null);
        }}
      />
    </View>
  );
}

// ── Zone list item ──────────────────────────────────────────────

function ZoneListItem({
  zone,
  onPress,
  onEdit,
  onToggle,
  onDelete,
}: {
  zone: Zone;
  onPress: () => void;
  onEdit: () => void;
  onToggle: () => void;
  onDelete: () => void;
}) {
  return (
    <Pressable style={styles.zoneItem} onPress={onPress} onLongPress={onEdit}>
      <View style={styles.zoneInfo}>
        <Text style={styles.zoneName}>{zone.name}</Text>
        <View style={styles.zoneMetaRow}>
          <View style={styles.radiusBadge}>
            <Text style={styles.radiusBadgeText}>
              {zone.radius_meters}m
            </Text>
          </View>
          <Text style={styles.zoneCoords}>
            {zone.latitude.toFixed(3)}, {zone.longitude.toFixed(3)}
          </Text>
        </View>
      </View>

      <View style={styles.zoneActions}>
        <Switch
          value={zone.enabled}
          onValueChange={onToggle}
          trackColor={{ false: '#d1d5db', true: '#93c5fd' }}
          thumbColor={zone.enabled ? '#2563eb' : '#9ca3af'}
        />
        <Pressable
          style={styles.deleteBtn}
          onPress={onDelete}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Ionicons name="trash-outline" size={18} color="#ef4444" />
        </Pressable>
      </View>
    </Pressable>
  );
}

// ── Styles ──────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },

  // Map
  mapContainer: {
    flex: 1,
    minHeight: 250,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  },
  zoneCountBadge: {
    position: 'absolute',
    top: 12,
    left: 12,
    backgroundColor: 'rgba(255,255,255,0.9)',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 12,
  },
  zoneCountText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
  },
  warningBadge: {
    position: 'absolute',
    top: 12,
    right: 12,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,251,235,0.95)',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 12,
    gap: 4,
  },
  warningText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#d97706',
  },

  // Empty state
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#374151',
    marginTop: 12,
    marginBottom: 6,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    maxWidth: 260,
  },

  // Zone list
  list: {
    flex: 1,
    maxHeight: '45%',
  },
  listContent: {
    padding: 12,
    paddingBottom: 80,
  },
  zoneItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#e5e7eb',
  },
  zoneInfo: {
    flex: 1,
  },
  zoneName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  zoneMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  radiusBadge: {
    backgroundColor: '#eff6ff',
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  radiusBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#2563eb',
  },
  zoneCoords: {
    fontSize: 12,
    color: '#9ca3af',
  },
  zoneActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  deleteBtn: {
    padding: 4,
  },

  // FAB
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2563eb',
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
  },

  // Error
  errorText: {
    fontSize: 16,
    color: '#ef4444',
    textAlign: 'center',
    marginVertical: 16,
    maxWidth: 280,
  },
  retryButton: {
    paddingVertical: 10,
    paddingHorizontal: 24,
    backgroundColor: '#2563eb',
    borderRadius: 8,
  },
  retryBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  inlineError: {
    fontSize: 14,
    color: '#ef4444',
    textAlign: 'center',
    marginTop: 8,
  },
});
