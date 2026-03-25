/**
 * recurrence-editor.js — RRULE & EXDATE editor widgets for SHACL form fields.
 *
 * Exports:
 *   window.initRecurrenceEditor(inputEl)  — enhances a text input for bpkm:recurrenceRule
 *   window.initExdateEditor(inputEl)      — enhances a text input for bpkm:exceptionDates
 *
 * Popovers are appended to document.body to escape dockview stacking contexts.
 * Click-outside and Escape dismiss popovers.
 */
(function () {
  'use strict';

  // ── RRULE presets ──────────────────────────────────────────────────
  var PRESETS = [
    { label: 'Daily',     value: 'FREQ=DAILY' },
    { label: 'Weekdays',  value: 'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR' },
    { label: 'Weekly',    value: 'FREQ=WEEKLY' },
    { label: 'Biweekly',  value: 'FREQ=WEEKLY;INTERVAL=2' },
    { label: 'Monthly',   value: 'FREQ=MONTHLY' },
    { label: 'Custom',    value: '__custom__' }
  ];

  var FREQ_OPTIONS = ['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'];
  var DAYS = [
    { code: 'MO', label: 'Mon' },
    { code: 'TU', label: 'Tue' },
    { code: 'WE', label: 'Wed' },
    { code: 'TH', label: 'Thu' },
    { code: 'FR', label: 'Fri' },
    { code: 'SA', label: 'Sat' },
    { code: 'SU', label: 'Sun' }
  ];

  // ── Human-readable summary ─────────────────────────────────────────
  function rruleToSummary(rrule) {
    if (!rrule) return '';
    var parts = {};
    rrule.split(';').forEach(function (seg) {
      var kv = seg.split('=');
      if (kv.length === 2) parts[kv[0]] = kv[1];
    });

    var freq = parts.FREQ || '';
    var interval = parseInt(parts.INTERVAL || '1', 10);
    var byday = parts.BYDAY || '';
    var count = parts.COUNT ? parseInt(parts.COUNT, 10) : null;
    var until = parts.UNTIL || '';

    var base = '';
    if (freq === 'DAILY') {
      base = interval === 1 ? 'Every day' : 'Every ' + interval + ' days';
    } else if (freq === 'WEEKLY') {
      if (byday === 'MO,TU,WE,TH,FR') {
        base = interval === 1 ? 'Every weekday' : 'Every ' + interval + ' weeks, weekdays';
      } else if (byday) {
        var dayNames = byday.split(',').map(function (d) {
          return _dayCodeToName(d);
        });
        base = interval === 1
          ? 'Every ' + dayNames.join(', ')
          : 'Every ' + interval + ' weeks on ' + dayNames.join(', ');
      } else {
        base = interval === 1 ? 'Every week' : 'Every ' + interval + ' weeks';
      }
    } else if (freq === 'MONTHLY') {
      base = interval === 1 ? 'Every month' : 'Every ' + interval + ' months';
    } else if (freq === 'YEARLY') {
      base = interval === 1 ? 'Every year' : 'Every ' + interval + ' years';
    } else {
      return rrule; // fallback to raw
    }

    if (count) base += ', ' + count + ' times';
    if (until) base += ', until ' + _formatUntilDate(until);
    return base;
  }

  function _dayCodeToName(code) {
    var map = { MO: 'Monday', TU: 'Tuesday', WE: 'Wednesday', TH: 'Thursday', FR: 'Friday', SA: 'Saturday', SU: 'Sunday' };
    return map[code] || code;
  }

  function _formatUntilDate(until) {
    // UNTIL is YYYYMMDD or YYYYMMDDTHHMMSSZ
    if (until.length >= 8) {
      return until.substring(0, 4) + '-' + until.substring(4, 6) + '-' + until.substring(6, 8);
    }
    return until;
  }

  // ── Parse existing RRULE into parts ────────────────────────────────
  function parseRrule(rrule) {
    var result = { freq: 'WEEKLY', interval: 1, byday: [], endType: 'never', count: '', until: '' };
    if (!rrule) return result;
    rrule.split(';').forEach(function (seg) {
      var kv = seg.split('=');
      if (kv.length !== 2) return;
      var key = kv[0], val = kv[1];
      if (key === 'FREQ') result.freq = val;
      else if (key === 'INTERVAL') result.interval = parseInt(val, 10) || 1;
      else if (key === 'BYDAY') result.byday = val.split(',');
      else if (key === 'COUNT') { result.endType = 'count'; result.count = val; }
      else if (key === 'UNTIL') { result.endType = 'until'; result.until = _untilToInputDate(val); }
    });
    return result;
  }

  function _untilToInputDate(val) {
    if (val.length >= 8) return val.substring(0, 4) + '-' + val.substring(4, 6) + '-' + val.substring(6, 8);
    return val;
  }

  // ── Build RRULE string from custom form state ──────────────────────
  function buildCustomRrule(state) {
    var parts = ['FREQ=' + state.freq];
    if (state.interval > 1) parts.push('INTERVAL=' + state.interval);
    if (state.freq === 'WEEKLY' && state.byday.length > 0) {
      parts.push('BYDAY=' + state.byday.join(','));
    }
    if (state.endType === 'count' && state.count) {
      parts.push('COUNT=' + state.count);
    } else if (state.endType === 'until' && state.until) {
      // Convert YYYY-MM-DD to YYYYMMDD
      parts.push('UNTIL=' + state.until.replace(/-/g, ''));
    }
    return parts.join(';');
  }

  // ── Find matching preset for an RRULE string ──────────────────────
  function findMatchingPreset(rrule) {
    if (!rrule) return null;
    for (var i = 0; i < PRESETS.length - 1; i++) { // skip Custom
      if (PRESETS[i].value === rrule) return PRESETS[i].value;
    }
    return '__custom__';
  }

  // ── Popover positioning helper ─────────────────────────────────────
  function positionPopover(popover, anchorEl) {
    var rect = anchorEl.getBoundingClientRect();
    var top = rect.bottom + 4;
    var left = rect.left;

    // Keep within viewport
    var pw = 320;
    if (left + pw > window.innerWidth - 8) left = window.innerWidth - pw - 8;
    if (left < 8) left = 8;
    if (top + 400 > window.innerHeight) top = rect.top - 400 - 4;

    popover.style.top = top + 'px';
    popover.style.left = left + 'px';
  }

  // ── Dismiss logic ──────────────────────────────────────────────────
  function setupDismiss(popover, cleanup) {
    function onClickOutside(e) {
      if (!popover.contains(e.target)) {
        cleanup();
      }
    }
    function onKeydown(e) {
      if (e.key === 'Escape') {
        cleanup();
      }
    }
    // Delay to avoid the click that opened the popover from immediately closing it
    setTimeout(function () {
      document.addEventListener('mousedown', onClickOutside, true);
      document.addEventListener('keydown', onKeydown, true);
    }, 0);

    return function teardown() {
      document.removeEventListener('mousedown', onClickOutside, true);
      document.removeEventListener('keydown', onKeydown, true);
    };
  }

  // ═══════════════════════════════════════════════════════════════════
  //  initRecurrenceEditor
  // ═══════════════════════════════════════════════════════════════════
  window.SemPKM.initRecurrenceEditor = function (inputEl) {
    if (!inputEl || inputEl.dataset.rruleInit) return;
    inputEl.dataset.rruleInit = '1';

    // Wrap the input and button in a flex row
    var wrapper = document.createElement('div');
    wrapper.className = 'rrule-editor-wrapper';
    inputEl.parentNode.insertBefore(wrapper, inputEl);
    wrapper.appendChild(inputEl);

    // Summary overlay
    var summary = document.createElement('span');
    summary.className = 'rrule-summary';
    wrapper.appendChild(summary);

    // Button to open editor
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rrule-editor-btn';
    btn.title = 'Edit recurrence rule';
    btn.innerHTML = '&#8635;'; // ↻
    wrapper.appendChild(btn);

    var popover = null;
    var teardown = null;

    function updateSummary() {
      var val = inputEl.value.trim();
      if (val) {
        summary.textContent = rruleToSummary(val);
        summary.style.display = '';
        inputEl.classList.add('rrule-has-summary');
      } else {
        summary.textContent = '';
        summary.style.display = 'none';
        inputEl.classList.remove('rrule-has-summary');
      }
    }
    updateSummary();

    function closePopover() {
      if (popover && popover.parentNode) popover.parentNode.removeChild(popover);
      if (teardown) teardown();
      popover = null;
      teardown = null;
    }

    function applyValue(rrule) {
      inputEl.value = rrule;
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      updateSummary();
    }

    function openPopover() {
      if (popover) { closePopover(); return; }

      popover = document.createElement('div');
      popover.className = 'rrule-popover';
      document.body.appendChild(popover);
      positionPopover(popover, wrapper);

      var currentRrule = inputEl.value.trim();
      var matchedPreset = findMatchingPreset(currentRrule);
      var parsed = parseRrule(currentRrule);

      // ── Header ──
      var header = document.createElement('div');
      header.className = 'rrule-popover-header';
      header.textContent = 'Recurrence';
      popover.appendChild(header);

      // ── Preset section ──
      var presetsDiv = document.createElement('div');
      presetsDiv.className = 'rrule-presets';
      popover.appendChild(presetsDiv);

      var radioName = 'rrule-preset-' + Date.now();
      var customSection = null;

      PRESETS.forEach(function (preset) {
        var label = document.createElement('label');
        label.className = 'rrule-preset-option';
        var radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = radioName;
        radio.value = preset.value;
        if (matchedPreset === preset.value) radio.checked = true;
        label.appendChild(radio);
        var span = document.createElement('span');
        span.textContent = preset.label;
        label.appendChild(span);
        presetsDiv.appendChild(label);

        radio.addEventListener('change', function () {
          if (preset.value === '__custom__') {
            showCustom();
          } else {
            hideCustom();
            applyValue(preset.value);
          }
        });
      });

      // ── Custom section ──
      customSection = document.createElement('div');
      customSection.className = 'rrule-custom';
      customSection.style.display = (matchedPreset === '__custom__') ? '' : 'none';
      popover.appendChild(customSection);

      buildCustomUI(customSection, parsed, function (state) {
        var rrule = buildCustomRrule(state);
        applyValue(rrule);
      });

      function showCustom() { customSection.style.display = ''; }
      function hideCustom() { customSection.style.display = 'none'; }

      // ── Clear button ──
      var footer = document.createElement('div');
      footer.className = 'rrule-popover-footer';
      var clearBtn = document.createElement('button');
      clearBtn.type = 'button';
      clearBtn.className = 'btn btn-sm rrule-clear-btn';
      clearBtn.textContent = 'Clear';
      clearBtn.addEventListener('click', function () {
        applyValue('');
        closePopover();
      });
      footer.appendChild(clearBtn);

      var doneBtn = document.createElement('button');
      doneBtn.type = 'button';
      doneBtn.className = 'btn btn-sm btn-primary rrule-done-btn';
      doneBtn.textContent = 'Done';
      doneBtn.addEventListener('click', function () {
        closePopover();
      });
      footer.appendChild(doneBtn);
      popover.appendChild(footer);

      teardown = setupDismiss(popover, closePopover);
    }

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      openPopover();
    });

    // Keep summary in sync if user edits the raw input directly
    inputEl.addEventListener('input', updateSummary);
  };

  // ── Build custom controls inside the custom section ────────────────
  function buildCustomUI(container, state, onChange) {
    container.innerHTML = '';

    // Frequency row
    var freqRow = document.createElement('div');
    freqRow.className = 'rrule-custom-row';
    var freqLabel = document.createElement('label');
    freqLabel.textContent = 'Repeat';
    freqRow.appendChild(freqLabel);
    var freqSelect = document.createElement('select');
    freqSelect.className = 'form-select rrule-custom-select';
    FREQ_OPTIONS.forEach(function (f) {
      var opt = document.createElement('option');
      opt.value = f;
      opt.textContent = f.charAt(0) + f.slice(1).toLowerCase();
      if (f === state.freq) opt.selected = true;
      freqSelect.appendChild(opt);
    });
    freqRow.appendChild(freqSelect);
    container.appendChild(freqRow);

    // Interval row
    var intRow = document.createElement('div');
    intRow.className = 'rrule-custom-row';
    var intLabel = document.createElement('label');
    intLabel.textContent = 'Every';
    intRow.appendChild(intLabel);
    var intInput = document.createElement('input');
    intInput.type = 'number';
    intInput.className = 'form-input rrule-custom-interval';
    intInput.min = '1';
    intInput.max = '99';
    intInput.value = state.interval;
    intRow.appendChild(intInput);
    var intSuffix = document.createElement('span');
    intSuffix.className = 'rrule-interval-suffix';
    intSuffix.textContent = _freqUnit(state.freq);
    intRow.appendChild(intSuffix);
    container.appendChild(intRow);

    // Day checkboxes (weekly only)
    var daysDiv = document.createElement('div');
    daysDiv.className = 'rrule-day-checkboxes';
    if (state.freq !== 'WEEKLY') daysDiv.style.display = 'none';
    DAYS.forEach(function (d) {
      var dayLabel = document.createElement('label');
      dayLabel.className = 'rrule-day-label';
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.value = d.code;
      if (state.byday.indexOf(d.code) >= 0) cb.checked = true;
      cb.addEventListener('change', fireChange);
      dayLabel.appendChild(cb);
      var daySpan = document.createElement('span');
      daySpan.textContent = d.label;
      dayLabel.appendChild(daySpan);
      daysDiv.appendChild(dayLabel);
    });
    container.appendChild(daysDiv);

    // End condition
    var endRow = document.createElement('div');
    endRow.className = 'rrule-custom-row';
    var endLabel = document.createElement('label');
    endLabel.textContent = 'Ends';
    endRow.appendChild(endLabel);
    var endSelect = document.createElement('select');
    endSelect.className = 'form-select rrule-custom-select';
    [{ value: 'never', label: 'Never' }, { value: 'count', label: 'After N times' }, { value: 'until', label: 'On date' }].forEach(function (opt) {
      var o = document.createElement('option');
      o.value = opt.value;
      o.textContent = opt.label;
      if (opt.value === state.endType) o.selected = true;
      endSelect.appendChild(o);
    });
    endRow.appendChild(endSelect);
    container.appendChild(endRow);

    // Count input
    var countRow = document.createElement('div');
    countRow.className = 'rrule-custom-row rrule-end-detail';
    countRow.style.display = state.endType === 'count' ? '' : 'none';
    var countInput = document.createElement('input');
    countInput.type = 'number';
    countInput.className = 'form-input rrule-custom-interval';
    countInput.min = '1';
    countInput.max = '999';
    countInput.value = state.count || '10';
    countInput.placeholder = 'Occurrences';
    countInput.addEventListener('input', fireChange);
    var countLabel = document.createElement('label');
    countLabel.textContent = 'occurrences';
    countRow.appendChild(countInput);
    countRow.appendChild(countLabel);
    container.appendChild(countRow);

    // Until date input
    var untilRow = document.createElement('div');
    untilRow.className = 'rrule-custom-row rrule-end-detail';
    untilRow.style.display = state.endType === 'until' ? '' : 'none';
    var untilInput = document.createElement('input');
    untilInput.type = 'date';
    untilInput.className = 'form-input';
    untilInput.value = state.until || '';
    untilInput.addEventListener('input', fireChange);
    untilRow.appendChild(untilInput);
    container.appendChild(untilRow);

    // Wire up change listeners
    freqSelect.addEventListener('change', function () {
      daysDiv.style.display = freqSelect.value === 'WEEKLY' ? '' : 'none';
      intSuffix.textContent = _freqUnit(freqSelect.value);
      fireChange();
    });
    intInput.addEventListener('input', fireChange);
    endSelect.addEventListener('change', function () {
      countRow.style.display = endSelect.value === 'count' ? '' : 'none';
      untilRow.style.display = endSelect.value === 'until' ? '' : 'none';
      fireChange();
    });

    function fireChange() {
      var selectedDays = [];
      daysDiv.querySelectorAll('input[type="checkbox"]:checked').forEach(function (cb) {
        selectedDays.push(cb.value);
      });
      onChange({
        freq: freqSelect.value,
        interval: parseInt(intInput.value, 10) || 1,
        byday: selectedDays,
        endType: endSelect.value,
        count: countInput.value,
        until: untilInput.value
      });
    }
  }

  function _freqUnit(freq) {
    var map = { DAILY: 'day(s)', WEEKLY: 'week(s)', MONTHLY: 'month(s)', YEARLY: 'year(s)' };
    return map[freq] || '';
  }

  // ═══════════════════════════════════════════════════════════════════
  //  initExdateEditor
  // ═══════════════════════════════════════════════════════════════════
  window.SemPKM.initExdateEditor = function (inputEl) {
    if (!inputEl || inputEl.dataset.exdateInit) return;
    inputEl.dataset.exdateInit = '1';

    // Wrap the input and button
    var wrapper = document.createElement('div');
    wrapper.className = 'exdate-editor-wrapper';
    inputEl.parentNode.insertBefore(wrapper, inputEl);
    wrapper.appendChild(inputEl);

    // Summary overlay
    var summary = document.createElement('span');
    summary.className = 'exdate-summary';
    wrapper.appendChild(summary);

    // Button
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rrule-editor-btn';
    btn.title = 'Manage exception dates';
    btn.textContent = '✕';
    wrapper.appendChild(btn);

    var popover = null;
    var teardown = null;

    function getDates() {
      var val = inputEl.value.trim();
      if (!val) return [];
      return val.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    }

    function setDates(dates) {
      inputEl.value = dates.join(',');
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      updateSummary();
    }

    function updateSummary() {
      var dates = getDates();
      if (dates.length > 0) {
        summary.textContent = dates.length + ' exception' + (dates.length === 1 ? '' : 's');
        summary.style.display = '';
        inputEl.classList.add('rrule-has-summary');
      } else {
        summary.textContent = '';
        summary.style.display = 'none';
        inputEl.classList.remove('rrule-has-summary');
      }
    }
    updateSummary();

    function closePopover() {
      if (popover && popover.parentNode) popover.parentNode.removeChild(popover);
      if (teardown) teardown();
      popover = null;
      teardown = null;
    }

    function openPopover() {
      if (popover) { closePopover(); return; }

      popover = document.createElement('div');
      popover.className = 'rrule-popover exdate-popover';
      document.body.appendChild(popover);
      positionPopover(popover, wrapper);

      var header = document.createElement('div');
      header.className = 'rrule-popover-header';
      header.textContent = 'Exception Dates';
      popover.appendChild(header);

      var listDiv = document.createElement('div');
      listDiv.className = 'exdate-list';
      popover.appendChild(listDiv);

      function renderList() {
        listDiv.innerHTML = '';
        var dates = getDates();
        if (dates.length === 0) {
          var empty = document.createElement('div');
          empty.className = 'exdate-empty';
          empty.textContent = 'No exception dates';
          listDiv.appendChild(empty);
          return;
        }
        dates.forEach(function (d, i) {
          var row = document.createElement('div');
          row.className = 'exdate-item';
          var label = document.createElement('span');
          label.className = 'exdate-date-label';
          label.textContent = d;
          row.appendChild(label);
          var removeBtn = document.createElement('button');
          removeBtn.type = 'button';
          removeBtn.className = 'exdate-remove-btn';
          removeBtn.title = 'Remove';
          removeBtn.textContent = '×';
          removeBtn.addEventListener('click', function () {
            var current = getDates();
            current.splice(i, 1);
            setDates(current);
            renderList();
          });
          row.appendChild(removeBtn);
          listDiv.appendChild(row);
        });
      }
      renderList();

      // Add date row
      var addRow = document.createElement('div');
      addRow.className = 'exdate-add-row';
      var dateInput = document.createElement('input');
      dateInput.type = 'date';
      dateInput.className = 'form-input exdate-date-input';
      addRow.appendChild(dateInput);
      var addBtn = document.createElement('button');
      addBtn.type = 'button';
      addBtn.className = 'btn btn-sm btn-primary';
      addBtn.textContent = 'Add';
      addBtn.addEventListener('click', function () {
        if (!dateInput.value) return;
        var current = getDates();
        if (current.indexOf(dateInput.value) < 0) {
          current.push(dateInput.value);
          current.sort();
          setDates(current);
        }
        dateInput.value = '';
        renderList();
      });
      addRow.appendChild(addBtn);
      popover.appendChild(addRow);

      // Footer
      var footer = document.createElement('div');
      footer.className = 'rrule-popover-footer';
      var doneBtn = document.createElement('button');
      doneBtn.type = 'button';
      doneBtn.className = 'btn btn-sm btn-primary rrule-done-btn';
      doneBtn.textContent = 'Done';
      doneBtn.addEventListener('click', closePopover);
      footer.appendChild(doneBtn);
      popover.appendChild(footer);

      teardown = setupDismiss(popover, closePopover);
    }

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      openPopover();
    });

    inputEl.addEventListener('input', updateSummary);
  };

  console.log('[recurrence-editor] loaded');

})();
