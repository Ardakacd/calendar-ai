import React, { useState, useEffect, useRef, useCallback } from "react";
import { View, StyleSheet, ScrollView, TouchableOpacity, KeyboardAvoidingView, Platform } from "react-native";
import { Modal, Portal, Text, TextInput } from "react-native-paper";
import DateTimePicker from "@react-native-community/datetimepicker";
import { MaterialIcons } from "@expo/vector-icons";
import NumericInput from "./NumericInput";
import { Event, SeriesUpdateRequest } from "../models/event";
import { showErrorToast, showSuccessToast } from "../common/toast/toast-message";
import { formatDateTime, toLocalISOString } from "../utils/datetime/dateUtils";
import { Colors, Radius, Shadow, getCategoryColor } from "../theme";
import { EventCategory } from "../models/event";

const CATEGORIES: EventCategory[] = ['work', 'personal', 'health', 'social'];
const MAX_DESCRIPTION_LENGTH = 5000;
type UpdateScope = 'single' | 'all' | 'future';

interface UpdateEventModalProps {
  visible: boolean;
  event: Event | null;
  onDismiss: () => void;
  onUpdate: (eventId: string, updatedEvent: Partial<Event>) => Promise<void>;
  onUpdateSeries?: (recurrenceId: string, request: SeriesUpdateRequest) => Promise<void>;
}

export default function UpdateEventModal({ visible, event, onDismiss, onUpdate, onUpdateSeries }: UpdateEventModalProps) {
  const titleRef = useRef("");
  const descriptionRef = useRef("");
  const locationRef = useRef("");
  const durationRef = useRef("");
  const [category, setCategory] = useState<EventCategory | undefined>(undefined);
  const [datetime, setDatetime] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [loading, setLoading] = useState(false);
  const [scope, setScope] = useState<UpdateScope>('single');
  // Key to force re-mount TextInputs when event changes (resets defaultValue)
  const [inputKey, setInputKey] = useState(0);

  useEffect(() => {
    if (event) {
      titleRef.current = event.title;
      descriptionRef.current = event.description || "";
      locationRef.current = event.location || "";
      durationRef.current = event.duration ? event.duration.toString() : "";
      setCategory(event.category);
      setDatetime(new Date(event.startDate));
      setScope('single');
      setInputKey(k => k + 1);
    }
  }, [event]);

  const handleUpdate = async () => {
    if (!event) return;
    const trimmedTitle = titleRef.current.trim();
    const trimmedDesc = descriptionRef.current.trim();
    const trimmedLocation = locationRef.current.trim();
    const durationStr = durationRef.current;

    if (!trimmedTitle) { showErrorToast("Title is required"); return; }
    if (trimmedTitle.length > 255) { showErrorToast("Title cannot be longer than 255 characters"); return; }
    if (trimmedDesc.length > MAX_DESCRIPTION_LENGTH) {
      showErrorToast(`Notes cannot be longer than ${MAX_DESCRIPTION_LENGTH} characters`);
      return;
    }

    let durationMinutes: number | undefined;
    if (durationStr) {
      try {
        durationMinutes = parseInt(durationStr);
        if (durationMinutes <= 0) { showErrorToast("Duration must be greater than 0"); return; }
      } catch {
        showErrorToast("Invalid duration format");
        return;
      }
    }

    try {
      setLoading(true);

      if (scope !== 'single' && event.recurrence_id && onUpdateSeries) {
        const oldStart = new Date(event.startDate);
        const newStart = datetime;
        const timeShiftMinutes = Math.round((newStart.getTime() - oldStart.getTime()) / 60000);
        const request: SeriesUpdateRequest = {
          scope,
          from_date: scope === 'future' ? toLocalISOString(new Date(event.startDate)) : undefined,
          title: trimmedTitle,
          category,
          description: trimmedDesc,
          location: trimmedLocation || undefined,
          duration: durationMinutes,
          time_shift_minutes: timeShiftMinutes !== 0 ? timeShiftMinutes : undefined,
        };
        await onUpdateSeries(event.recurrence_id, request);
      } else {
        await onUpdate(event.id, {
          title: trimmedTitle,
          category,
          description: trimmedDesc,
          location: trimmedLocation || undefined,
          duration: durationMinutes,
          startDate: toLocalISOString(datetime),
        });
      }

      onDismiss();
      showSuccessToast("Event updated successfully");
    } catch (error: any) {
      showErrorToast(error.response?.data?.detail || "Event could not be updated");
    } finally {
      setLoading(false);
    }
  };

  const onDateChange = (_: any, selectedDate?: Date) => {
    if (selectedDate) setDatetime(selectedDate);
  };

  return (
    <Portal>
      <Modal
        visible={visible}
        onDismiss={onDismiss}
        contentContainerStyle={styles.overlay}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.sheet}
        >
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>Edit Event</Text>
            <TouchableOpacity onPress={onDismiss} style={styles.closeBtn}>
              <MaterialIcons name="close" size={20} color={Colors.textSecondary} />
            </TouchableOpacity>
          </View>

          <ScrollView
            showsVerticalScrollIndicator={false}
            style={styles.body}
            keyboardShouldPersistTaps="handled"
          >
            {/* Scope picker — only shown for recurring events */}
            {event?.recurrence_type && (
              <View style={styles.field}>
                <Text style={styles.label}>Edit scope</Text>
                <View style={styles.scopeRow}>
                  {([
                    { value: 'single', label: 'This event' },
                    { value: 'future', label: 'This & future' },
                    { value: 'all',    label: 'All events' },
                  ] as { value: UpdateScope; label: string }[]).map(({ value, label }) => (
                    <TouchableOpacity
                      key={value}
                      style={[styles.scopeChip, scope === value && styles.scopeChipActive]}
                      onPress={() => setScope(value)}
                      activeOpacity={0.7}
                    >
                      <Text style={[styles.scopeChipText, scope === value && styles.scopeChipTextActive]}>
                        {label}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            )}

            {/* Title */}
            <View style={styles.field}>
              <Text style={styles.label}>Title *</Text>
              <TextInput
                key={`title-${inputKey}`}
                mode="outlined"
                defaultValue={titleRef.current}
                onChangeText={(t) => { titleRef.current = t; }}
                placeholder="What's the event?"
                style={styles.input}
                outlineColor={Colors.border}
                activeOutlineColor={Colors.primary}
                textColor={Colors.textPrimary}
                theme={{ roundness: Radius.md }}
              />
            </View>

            {/* Category */}
            <View style={styles.field}>
              <View style={styles.labelRow}>
                <Text style={styles.label}>Category</Text>
                <Text style={styles.optional}>optional</Text>
              </View>
              <View style={styles.categoryRow}>
                {CATEGORIES.map((cat) => {
                  const col = getCategoryColor(cat);
                  const selected = category === cat;
                  return (
                    <TouchableOpacity
                      key={cat}
                      style={[styles.categoryChip, { backgroundColor: selected ? col.accent : col.bg }]}
                      onPress={() => setCategory(selected ? undefined : cat)}
                      activeOpacity={0.7}
                    >
                      <Text style={[styles.categoryChipText, { color: selected ? '#fff' : col.text }]}>
                        {cat}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>

            {/* Description */}
            <View style={styles.field}>
              <View style={styles.labelRow}>
                <Text style={styles.label}>Notes</Text>
                <Text style={styles.optional}>optional</Text>
              </View>
              <TextInput
                key={`desc-${inputKey}`}
                mode="outlined"
                defaultValue={descriptionRef.current}
                onChangeText={(t) => { descriptionRef.current = t; }}
                placeholder="Add notes..."
                multiline
                numberOfLines={3}
                scrollEnabled={false}
                style={[styles.input, styles.multilineInput]}
                outlineColor={Colors.border}
                activeOutlineColor={Colors.primary}
                textColor={Colors.textPrimary}
                theme={{ roundness: Radius.md }}
              />
            </View>

            {/* Date & Time */}
            <View style={styles.field}>
              <Text style={styles.label}>Date & Time *</Text>
              <TouchableOpacity
                style={styles.dateBtn}
                onPress={() => setShowDatePicker(true)}
                activeOpacity={0.7}
              >
                <MaterialIcons name="calendar-today" size={16} color={Colors.primary} />
                <Text style={styles.dateBtnText}>{formatDateTime(toLocalISOString(datetime))}</Text>
                <MaterialIcons name="keyboard-arrow-down" size={18} color={Colors.textTertiary} />
              </TouchableOpacity>
              {showDatePicker && (
                <DateTimePicker
                  value={datetime}
                  mode="datetime"
                  display="default"
                  locale="en-US"
                  onChange={onDateChange}
                />
              )}
            </View>

            {/* Duration */}
            <View style={styles.field}>
              <View style={styles.labelRow}>
                <Text style={styles.label}>Duration</Text>
                <Text style={styles.optional}>optional</Text>
              </View>
              <NumericInput
                key={`dur-${inputKey}`}
                mode="outlined"
                value={durationRef.current}
                onValueChange={(t) => { durationRef.current = t; }}
                placeholder="Minutes (e.g. 30)"
                style={styles.input}
                outlineColor={Colors.border}
                activeOutlineColor={Colors.primary}
                textColor={Colors.textPrimary}
                theme={{ roundness: Radius.md }}
              />
            </View>

            {/* Location */}
            <View style={styles.field}>
              <View style={styles.labelRow}>
                <Text style={styles.label}>Location</Text>
                <Text style={styles.optional}>optional</Text>
              </View>
              <TextInput
                key={`loc-${inputKey}`}
                mode="outlined"
                defaultValue={locationRef.current}
                onChangeText={(t) => { locationRef.current = t; }}
                placeholder="Where?"
                style={styles.input}
                outlineColor={Colors.border}
                activeOutlineColor={Colors.primary}
                textColor={Colors.textPrimary}
                theme={{ roundness: Radius.md }}
              />
            </View>
          </ScrollView>

          {/* Actions */}
          <View style={styles.actions}>
            <TouchableOpacity style={styles.cancelBtn} onPress={onDismiss} disabled={loading}>
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.submitBtn, loading && styles.btnDisabled]}
              onPress={handleUpdate}
              disabled={loading}
              activeOpacity={0.85}
            >
              <Text style={styles.submitBtnText}>
                {loading ? "Saving..." : "Update Event"}
              </Text>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    margin: 0,
    padding: 0,
  },
  sheet: {
    backgroundColor: Colors.surface,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: "90%",
    ...Shadow.md,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  title: {
    fontSize: 18,
    fontWeight: "700",
    color: Colors.textPrimary,
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: Radius.full,
    backgroundColor: Colors.borderLight,
    alignItems: "center",
    justifyContent: "center",
  },
  body: {
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  field: {
    marginBottom: 18,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: Colors.textSecondary,
    marginBottom: 8,
    letterSpacing: 0.2,
  },
  labelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 8,
  },
  optional: {
    fontSize: 11,
    color: Colors.textTertiary,
    fontStyle: "italic",
  },
  input: {
    backgroundColor: Colors.surface,
  },
  multilineInput: {
    minHeight: 80,
  },
  scopeRow: {
    flexDirection: "row",
    gap: 8,
  },
  scopeChip: {
    flex: 1,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.md,
    paddingVertical: 9,
    alignItems: "center",
  },
  scopeChipActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primaryLight,
  },
  scopeChipText: {
    fontSize: 12,
    fontWeight: "500",
    color: Colors.textSecondary,
  },
  scopeChipTextActive: {
    color: Colors.primary,
    fontWeight: "600",
  },
  categoryRow: {
    flexDirection: "row",
    gap: 8,
    flexWrap: "wrap",
  },
  categoryChip: {
    borderRadius: Radius.full,
    paddingHorizontal: 14,
    paddingVertical: 7,
  },
  categoryChipText: {
    fontSize: 13,
    fontWeight: "600",
    textTransform: "capitalize",
  },
  dateBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.md,
    paddingHorizontal: 14,
    paddingVertical: 13,
  },
  dateBtnText: {
    flex: 1,
    fontSize: 15,
    color: Colors.textPrimary,
  },
  actions: {
    flexDirection: "row",
    gap: 12,
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 36,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  cancelBtn: {
    flex: 1,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: "center",
  },
  cancelBtnText: {
    fontSize: 15,
    fontWeight: "500",
    color: Colors.textSecondary,
  },
  submitBtn: {
    flex: 2,
    backgroundColor: Colors.primary,
    borderRadius: Radius.md,
    paddingVertical: 14,
    alignItems: "center",
    ...Shadow.sm,
  },
  btnDisabled: {
    opacity: 0.7,
  },
  submitBtnText: {
    fontSize: 15,
    fontWeight: "600",
    color: Colors.surface,
  },
});
