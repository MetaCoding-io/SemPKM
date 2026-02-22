/**
 * Column visibility toggle UI and localStorage persistence per type.
 *
 * Provides a ColumnPrefs object with methods to save/restore column
 * visibility preferences per type IRI in localStorage, toggle column
 * visibility via a dropdown UI, and reorder columns.
 */

(function () {
  'use strict';

  var STORAGE_PREFIX = 'col-prefs:';

  var ColumnPrefs = {

    /**
     * Get saved column visibility/order for a type.
     * Returns null if no prefs saved (show all defaults).
     */
    getVisibleColumns: function (typeIri) {
      try {
        var saved = localStorage.getItem(STORAGE_PREFIX + typeIri);
        if (saved) {
          return JSON.parse(saved);
        }
      } catch (e) {
        // localStorage might be blocked
      }
      return null;
    },

    /**
     * Save column preferences for a type.
     * columns: array of {col, visible, order}
     */
    saveColumnPrefs: function (typeIri, columns) {
      try {
        localStorage.setItem(STORAGE_PREFIX + typeIri, JSON.stringify(columns));
      } catch (e) {
        // localStorage might be full or blocked
      }
    },

    /**
     * Apply saved column preferences to the current table.
     * Hides columns by adding .col-hidden to matching data-col cells.
     */
    applyColumnPrefs: function (typeIri) {
      var prefs = this.getVisibleColumns(typeIri);
      if (!prefs) return;

      prefs.forEach(function (pref) {
        var cells = document.querySelectorAll('.view-table [data-col="' + pref.col + '"]');
        cells.forEach(function (cell) {
          if (pref.visible) {
            cell.classList.remove('col-hidden');
            cell.style.order = pref.order || '';
          } else {
            cell.classList.add('col-hidden');
          }
        });
      });
    },

    /**
     * Open a column settings dropdown/popover.
     * Anchored to the gear icon in the view toolbar.
     */
    openColumnSettings: function (typeIri, allColumns) {
      // Remove existing dropdown if open
      var existing = document.querySelector('.column-settings-dropdown');
      if (existing) {
        existing.remove();
        return;
      }

      // Get current prefs or build defaults
      var prefs = this.getVisibleColumns(typeIri);
      if (!prefs) {
        prefs = allColumns.map(function (col, i) {
          return { col: col, visible: true, order: i };
        });
      }

      // Build dropdown HTML
      var dropdown = document.createElement('div');
      dropdown.className = 'column-settings-dropdown';
      dropdown.innerHTML = '<div class="column-settings-header">Column Visibility</div>';

      var list = document.createElement('div');
      list.className = 'column-settings-list';

      prefs.forEach(function (pref, index) {
        var item = document.createElement('div');
        item.className = 'column-settings-item';

        var checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = pref.visible;
        checkbox.dataset.col = pref.col;
        checkbox.id = 'col-toggle-' + index;

        checkbox.addEventListener('change', function () {
          pref.visible = this.checked;
          ColumnPrefs.saveColumnPrefs(typeIri, prefs);
          ColumnPrefs.applyColumnPrefs(typeIri);
        });

        var label = document.createElement('label');
        label.htmlFor = 'col-toggle-' + index;
        label.textContent = pref.col.replace(/_/g, ' ').replace(/\b\w/g, function (c) {
          return c.toUpperCase();
        });

        var moveUp = document.createElement('button');
        moveUp.className = 'column-move-btn';
        moveUp.textContent = '\u25B2';
        moveUp.title = 'Move up';
        moveUp.addEventListener('click', function (e) {
          e.preventDefault();
          if (index > 0) {
            var temp = prefs[index - 1];
            prefs[index - 1] = prefs[index];
            prefs[index] = temp;
            // Update order values
            prefs.forEach(function (p, i) { p.order = i; });
            ColumnPrefs.saveColumnPrefs(typeIri, prefs);
            ColumnPrefs.applyColumnPrefs(typeIri);
            // Rebuild dropdown
            dropdown.remove();
            ColumnPrefs.openColumnSettings(typeIri, allColumns);
          }
        });

        var moveDown = document.createElement('button');
        moveDown.className = 'column-move-btn';
        moveDown.textContent = '\u25BC';
        moveDown.title = 'Move down';
        moveDown.addEventListener('click', function (e) {
          e.preventDefault();
          if (index < prefs.length - 1) {
            var temp = prefs[index + 1];
            prefs[index + 1] = prefs[index];
            prefs[index] = temp;
            prefs.forEach(function (p, i) { p.order = i; });
            ColumnPrefs.saveColumnPrefs(typeIri, prefs);
            ColumnPrefs.applyColumnPrefs(typeIri);
            dropdown.remove();
            ColumnPrefs.openColumnSettings(typeIri, allColumns);
          }
        });

        item.appendChild(checkbox);
        item.appendChild(label);
        item.appendChild(moveUp);
        item.appendChild(moveDown);
        list.appendChild(item);
      });

      dropdown.appendChild(list);

      // Position near the gear button
      var gearBtn = document.querySelector('.view-columns-btn');
      if (gearBtn) {
        gearBtn.parentElement.style.position = 'relative';
        gearBtn.parentElement.appendChild(dropdown);
      } else {
        document.body.appendChild(dropdown);
      }

      // Close on outside click
      function closeOnOutside(e) {
        if (!dropdown.contains(e.target) && e.target !== gearBtn) {
          dropdown.remove();
          document.removeEventListener('click', closeOnOutside);
        }
      }
      setTimeout(function () {
        document.addEventListener('click', closeOnOutside);
      }, 10);
    }
  };

  window.ColumnPrefs = ColumnPrefs;

})();
