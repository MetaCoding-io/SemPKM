/**
 * Zone editor modal for creating/editing geofence zones.
 *
 * Provides name input, radius adjustment (50–1000m) with +/- stepper
 * buttons, read-only lat/lon display (set via map tap in parent), and
 * Save/Cancel actions.
 *
 * For new zones, shows instruction text to tap the map. For existing
 * zones, pre-fills all fields from the zone data.
 *
 * @module components/ZoneEditor
 */

import React, { useEffect, useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import type { Zone } from '@/api/client';

// ── Types ───────────────────────────────────────────────────────

export interface ZoneEditorData {
  name: string;
  radius_meters: number;
  latitude: number;
  longitude: number;
}

interface ZoneEditorProps {
  visible: boolean;
  /** When provided, the editor is in "edit" mode and pre-fills fields. */
  zone?: Zone;
  /** Coordinates from map tap (new zone) or existing zone center. */
  center?: { latitude: number; longitude: number } | null;
  onSave: (data: ZoneEditorData) => void;
  onCancel: () => void;
}

// ── Constants ───────────────────────────────────────────────────

const MIN_RADIUS = 50;
const MAX_RADIUS = 1000;
const RADIUS_STEP = 50;
const MAX_NAME_LENGTH = 100;

// ── Component ───────────────────────────────────────────────────

export default function ZoneEditor({
  visible,
  zone,
  center,
  onSave,
  onCancel,
}: ZoneEditorProps) {
  const [name, setName] = useState('');
  const [radius, setRadius] = useState(200);

  // Reset form when modal opens or zone changes
  useEffect(() => {
    if (visible) {
      if (zone) {
        setName(zone.name);
        setRadius(zone.radius_meters);
      } else {
        setName('');
        setRadius(200);
      }
    }
  }, [visible, zone]);

  const isEditing = !!zone;
  const hasCenter = !!(center?.latitude && center?.longitude);
  const canSave = name.trim().length > 0 && hasCenter;

  const handleSave = () => {
    if (!canSave || !center) return;
    onSave({
      name: name.trim(),
      radius_meters: radius,
      latitude: center.latitude,
      longitude: center.longitude,
    });
  };

  const decreaseRadius = () => {
    setRadius((r) => Math.max(MIN_RADIUS, r - RADIUS_STEP));
  };

  const increaseRadius = () => {
    setRadius((r) => Math.min(MAX_RADIUS, r + RADIUS_STEP));
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onCancel}
    >
      <KeyboardAvoidingView
        style={styles.overlay}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View style={styles.sheet}>
          <Text style={styles.title}>
            {isEditing ? 'Edit Zone' : 'New Zone'}
          </Text>

          {/* Name input */}
          <Text style={styles.label}>Name</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={(text) => setName(text.slice(0, MAX_NAME_LENGTH))}
            placeholder="e.g. Home, Office, Gym"
            placeholderTextColor="#9ca3af"
            maxLength={MAX_NAME_LENGTH}
            autoFocus={!isEditing}
            returnKeyType="done"
          />

          {/* Radius stepper */}
          <Text style={styles.label}>Radius</Text>
          <View style={styles.stepperRow}>
            <Pressable
              style={[styles.stepperBtn, radius <= MIN_RADIUS && styles.stepperDisabled]}
              onPress={decreaseRadius}
              disabled={radius <= MIN_RADIUS}
            >
              <Text style={styles.stepperBtnText}>−</Text>
            </Pressable>
            <View style={styles.radiusDisplay}>
              <Text style={styles.radiusValue}>{radius}m</Text>
            </View>
            <Pressable
              style={[styles.stepperBtn, radius >= MAX_RADIUS && styles.stepperDisabled]}
              onPress={increaseRadius}
              disabled={radius >= MAX_RADIUS}
            >
              <Text style={styles.stepperBtnText}>+</Text>
            </Pressable>
          </View>

          {/* Coordinates display */}
          <Text style={styles.label}>Location</Text>
          {hasCenter ? (
            <View style={styles.coordsRow}>
              <Text style={styles.coordText}>
                {center!.latitude.toFixed(5)}, {center!.longitude.toFixed(5)}
              </Text>
            </View>
          ) : (
            <Text style={styles.instructionText}>
              Tap the map to set the zone center
            </Text>
          )}

          {/* Actions */}
          <View style={styles.actions}>
            <Pressable style={styles.cancelBtn} onPress={onCancel}>
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </Pressable>
            <Pressable
              style={[styles.saveBtn, !canSave && styles.saveBtnDisabled]}
              onPress={handleSave}
              disabled={!canSave}
            >
              <Text style={styles.saveBtnText}>
                {isEditing ? 'Update' : 'Create'}
              </Text>
            </Pressable>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// ── Styles ──────────────────────────────────────────────────────

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  sheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    paddingBottom: 40,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 20,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    backgroundColor: '#f3f4f6',
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
    fontSize: 16,
    color: '#111827',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#d1d5db',
  },

  // Radius stepper
  stepperRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stepperBtn: {
    width: 44,
    height: 44,
    borderRadius: 10,
    backgroundColor: '#e5e7eb',
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepperBtnText: {
    fontSize: 22,
    fontWeight: '600',
    color: '#374151',
  },
  stepperDisabled: {
    opacity: 0.3,
  },
  radiusDisplay: {
    flex: 1,
    alignItems: 'center',
  },
  radiusValue: {
    fontSize: 20,
    fontWeight: '600',
    color: '#111827',
  },

  // Coordinates
  coordsRow: {
    backgroundColor: '#f3f4f6',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  coordText: {
    fontSize: 14,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    color: '#374151',
  },
  instructionText: {
    fontSize: 14,
    color: '#9ca3af',
    fontStyle: 'italic',
    paddingVertical: 8,
  },

  // Actions
  actions: {
    flexDirection: 'row',
    marginTop: 24,
    gap: 12,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 10,
    backgroundColor: '#f3f4f6',
    alignItems: 'center',
  },
  cancelBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
  },
  saveBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 10,
    backgroundColor: '#2563eb',
    alignItems: 'center',
  },
  saveBtnDisabled: {
    opacity: 0.4,
  },
  saveBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});
