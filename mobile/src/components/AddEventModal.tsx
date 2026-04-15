import React, { useState, useEffect } from "react";
import { View, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import { Modal, Portal, Text, TextInput } from "react-native-paper";
import DateTimePicker from "@react-native-community/datetimepicker";
import { MaterialIcons } from "@expo/vector-icons";
import NumericInput from "./NumericInput";
import { EventCreate } from "../models/event";
import { showErrorToast, showSuccessToast } from "../common/toast/toast-message";
import {
  defaultDateTimeForCalendarDay,
  formatCalendarDayHeading,
  formatDateTime,
  toLocalISOString,
} from "../utils/datetime/dateUtils";
import { Colors, Radius, Shadow, getCategoryColor } from "../theme";
import { EventCategory } from "../models/event";

const CATEGORIES: EventCategory[] = ['work', 'personal', 'health', 'social'];
const MAX_DESCRIPTION_LENGTH = 5000;

interface AddEventModalProps {
  visible: boolean;
  onDismiss: () => void;
  onAdd: (event: EventCreate) => Promise<void>;
  onEdit?: (event: EventCreate) => Promise<void>;
  initialEvent?: EventCreate;
  mode?: "add" | "edit";
  /** When adding, pre-fill date/time for this calendar day (YYYY-MM-DD). */
  defaultCalendarDayKey?: string;
}

export default function AddEventModal({
  visible,
  onDismiss,
  onAdd,
  onEdit,
  initialEvent,
  mode = "add",
  defaultCalendarDayKey,
}: AddEventModalProps) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<EventCategory | undefined>(undefined);
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [duration, setDuration] = useState("");
  const [datetime, setDatetime] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialEvent && mode === "edit") {
      setTitle(initialEvent.title);
      setCategory(initialEvent.category);
      setDescription(initialEvent.description || "");
      setLocation(initialEvent.location || "");
      setDuration(initialEvent.duration ? initialEvent.duration.toString() : "");
      setDatetime(new Date(initialEvent.startDate));
    } else {
      setTitle("");
      setCategory(undefined);
      setDescription("");
      setLocation("");
      setDuration("");
      setDatetime(
        defaultCalendarDayKey
          ? defaultDateTimeForCalendarDay(defaultCalendarDayKey)
          : new Date()
      );
    }
  }, [initialEvent, mode, visible, defaultCalendarDayKey]);

  const handleSubmit = async () => {
    const trimmedTitle = title.trim();
    if (!trimmedTitle) { showErrorToast("Title is required"); return; }
    if (trimmedTitle.length > 255) { showErrorToast("Title cannot be longer than 255 characters"); return; }
    if (description.trim().length > MAX_DESCRIPTION_LENGTH) {
      showErrorToast(`Notes cannot be longer than ${MAX_DESCRIPTION_LENGTH} characters`);
      return;
    }

    let durationMinutes: number | undefined;
    if (duration) {
      durationMinutes = parseInt(duration);
      if (durationMinutes <= 0) { showErrorToast("Duration must be greater than 0"); return; }
    }

    const trimmedDescription = description.trim();
    const eventData: EventCreate = {
      title: trimmedTitle,
      category,
      description:
        mode === "edit" && onEdit && initialEvent
          ? trimmedDescription
          : trimmedDescription || undefined,
      location: location.trim() || undefined,
      duration: durationMinutes,
      startDate: toLocalISOString(datetime),
    };

    try {
      setLoading(true);
      if (mode === "edit" && onEdit && initialEvent) {
        await onEdit(eventData);
      } else {
        await onAdd(eventData);
        showSuccessToast("Event created successfully");
      }
      setTitle("");
      setLocation("");
      setDuration("");
      setDatetime(
        defaultCalendarDayKey
          ? defaultDateTimeForCalendarDay(defaultCalendarDayKey)
          : new Date()
      );
      onDismiss();
    } catch (error: any) {
      showErrorToast(error.response?.data?.detail || "Event could not be created");
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
        <View style={styles.sheet}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleBlock}>
              <Text style={styles.title}>
                {mode === "edit" ? "Edit Event" : "New Event"}
              </Text>
              {mode === "add" && defaultCalendarDayKey ? (
                <Text style={styles.headerSubtitle}>
                  {formatCalendarDayHeading(defaultCalendarDayKey)}
                </Text>
              ) : null}
            </View>
            <TouchableOpacity onPress={onDismiss} style={styles.closeBtn}>
              <MaterialIcons name="close" size={20} color={Colors.textSecondary} />
            </TouchableOpacity>
          </View>

          <ScrollView showsVerticalScrollIndicator={false} style={styles.body}>
            {/* Title */}
            <View style={styles.field}>
              <Text style={styles.label}>Title *</Text>
              <TextInput
                mode="outlined"
                value={title}
                onChangeText={setTitle}
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
                mode="outlined"
                value={description}
                onChangeText={setDescription}
                placeholder="Add notes..."
                multiline
                numberOfLines={3}
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
                mode="outlined"
                value={duration}
                onValueChange={setDuration}
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
                mode="outlined"
                value={location}
                onChangeText={setLocation}
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
              onPress={handleSubmit}
              disabled={loading}
              activeOpacity={0.85}
            >
              <Text style={styles.submitBtnText}>
                {loading ? "Saving..." : mode === "edit" ? "Update Event" : "Create Event"}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
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
    alignItems: "flex-start",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerTitleBlock: {
    flex: 1,
    marginRight: 12,
  },
  title: {
    fontSize: 18,
    fontWeight: "700",
    color: Colors.textPrimary,
  },
  headerSubtitle: {
    fontSize: 13,
    color: Colors.textSecondary,
    marginTop: 4,
    fontWeight: "500",
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
