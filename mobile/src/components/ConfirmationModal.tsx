import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  Modal,
  ScrollView,
  Alert,
} from 'react-native';
import {
  Text,
  Button,
  TextInput,
  IconButton,
  Card,
  Title,
  Paragraph,
} from 'react-native-paper';
import DateTimePicker from '@react-native-community/datetimepicker';
import { format } from 'date-fns';
import { EventConfirmationData } from '../models/event';


interface ConfirmationModalProps {
  visible: boolean;
  onDismiss: () => void;
  action: 'create' | 'update' | 'delete';
  eventData: EventConfirmationData;
  onConfirm: (data: EventConfirmationData) => void;
  isLoading?: boolean;
}

export default function ConfirmationModal({
  visible,
  onDismiss,
  action,
  eventData,
  onConfirm,
  isLoading = false,
}: ConfirmationModalProps) {
  const [editableData, setEditableData] = useState<EventConfirmationData>(eventData);
  const [editingField, setEditingField] = useState<string | null>(null);
  
  // Parse datetime string to Date object
  const parseDateTime = (dateTimeStr: string): Date => {
    try {
      return new Date(dateTimeStr);
    } catch {
      return new Date();
    }
  };

  // Format datetime for display
  const formatDateTime = (dateTimeStr: string): string => {
    try {
      const date = new Date(dateTimeStr);
      return format(date, 'MMM dd, yyyy HH:mm');
    } catch {
      return dateTimeStr;
    }
  };

  const handleEditField = (field: string) => {
    setEditingField(field);
  };

  const handleSaveField = (field: string, value: string | number) => {
    setEditableData(prev => ({
      ...prev,
      [field]: value,
    }));
    setEditingField(null);
  };

  const handleCancelEdit = () => {
    if (editingField) {
      setEditableData(prev => ({
        ...prev,
        [editingField]: eventData[editingField as keyof EventConfirmationData],
      }));
    }
    setEditingField(null);
  };

  const handleDateChange = (event: any, selectedDate?: Date) => {
    if (selectedDate) {
      const currentDateTime = parseDateTime(editableData.startDate);
      const newDateTime = new Date(
        selectedDate.getFullYear(),
        selectedDate.getMonth(),
        selectedDate.getDate(),
        currentDateTime.getHours(),
        currentDateTime.getMinutes()
      );
      setEditableData(prev => ({
        ...prev,
        'startDate': newDateTime.toISOString(),
      }));
    }
  };

  const handleTimeChange = (event: any, selectedTime?: Date) => {
    if (selectedTime) {
      const currentDateTime = parseDateTime(editableData.startDate);
      const newDateTime = new Date(
        currentDateTime.getFullYear(),
        currentDateTime.getMonth(),
        currentDateTime.getDate(),
        selectedTime.getHours(),
        selectedTime.getMinutes()
      );
      
      setEditableData(prev => ({
        ...prev,
        'startDate': newDateTime.toISOString(),
      }));
    }
  };

  const handleConfirm = () => {
      onConfirm(editableData);
  };

  const getActionTitle = () => {
    switch (action) {
      case 'create':
        return 'Add Event';
      case 'update':
        return 'Update Event';
      case 'delete':
        return 'Delete Event';
      default:
        return 'Confirm Action';
    }
  };

  const getActionText = () => {
    switch (action) {
      case 'create':
        return 'Please review and edit the event details below:';
      case 'update':
        return 'Please review and edit the updated event details:';
      case 'delete':
        return 'Please confirm that you want to delete this event:';
      default:
        return 'Please review and confirm the action:';
    }
  }

  const renderEditableField = (
    label: string,
    field: keyof EventConfirmationData,
    value: string | number | undefined,
    placeholder?: string,
    keyboardType: 'default' | 'numeric' = 'default'
  ) => {
    const isEditing = editingField === field;
    const isEditable = action !== 'delete';

    return (
      <View style={styles.fieldContainer}>
        <View style={styles.fieldHeader}>
          <Text style={styles.fieldLabel}>{label}</Text>
          {isEditable && !isEditing && (
            <IconButton
              icon="pencil"
              size={20}
              onPress={() => handleEditField(field)}
              style={styles.editButton}
              iconColor="#667eea"
            />
          )}
        </View>
        
        {isEditing ? (
          <View style={styles.editContainer}>
            <TextInput
              value={String(value || '')}
              onChangeText={(text) => {
                if (keyboardType === 'numeric') {
                  const numValue = parseInt(text) || 0;
                  setEditableData(prev => ({ ...prev, [field]: numValue }));
                } else {
                  setEditableData(prev => ({ ...prev, [field]: text }));
                }
              }}
              placeholder={placeholder}
              keyboardType={keyboardType}
              style={styles.textInput}
              autoFocus
            />
            <View style={styles.editButtons}>
              <IconButton
                icon="check"
                size={20}
                onPress={() => handleSaveField(field, editableData[field] || '')}
                style={styles.saveButton}
                iconColor="#ffffff"
              />
              <IconButton
                icon="close"
                size={20}
                onPress={handleCancelEdit}
                style={styles.cancelButton}
                iconColor="#ffffff"
              />
            </View>
          </View>
        ) : (
          <Text style={styles.fieldValue}>
            {field === 'startDate' ? formatDateTime(String(value || '')) : String(value || 'Not set')}
          </Text>
        )}
      </View>
    );
  };

  const renderDateTimeField = () => {
    const isEditing = editingField === 'datetime';
    const isEditable = action !== 'delete';

    return (
      <View style={styles.fieldContainer}>
        <View style={styles.fieldHeader}>
          <Text style={styles.fieldLabel}>Date & Time</Text>
          {isEditable && !isEditing && (
            <IconButton
              icon="pencil"
              size={20}
              onPress={() => handleEditField('startDate')}
              style={styles.editButton}
              iconColor="#667eea"
            />
          )}
        </View>
        
        {isEditing ? (
          <View style={styles.editContainer}>
            <View style={styles.datetimeButtons}>
            
            <DateTimePicker
              value={parseDateTime(editableData.startDate)}
              mode="date"
              onChange={handleDateChange}
            />
        
            <DateTimePicker
              value={parseDateTime(editableData.startDate)}
              mode="time"
              onChange={handleTimeChange}
            />
            </View>
            
            <View style={styles.editButtons}>
              <IconButton
                icon="check"
                size={20}
                onPress={() => handleSaveField('startDate', editableData.startDate)}
                style={styles.saveButton}
                iconColor="#ffffff"
              />
              <IconButton
                icon="close"
                size={20}
                onPress={handleCancelEdit}
                style={styles.cancelButton}
                iconColor="#ffffff"
              />
            </View>
          </View>
        ) : (
          <Text style={styles.fieldValue}>
            {formatDateTime(editableData.startDate)}
          </Text>
        )}
      </View>
    );
  };

  return (
    <Modal
      visible={visible}
      onDismiss={onDismiss}
      animationType="slide"
      transparent={true}
    >
      <View style={styles.modalOverlay}>
        <Card style={styles.modalCard}>
          <Card.Content>
            <Title style={styles.modalTitle}>{getActionTitle()}</Title>
            <Paragraph style={styles.modalSubtitle}>
              {getActionText()}
            </Paragraph>

            <ScrollView>
              {renderEditableField('Title', 'title', editableData.title, 'Enter event title')}
              
              {renderDateTimeField()}
              
              {renderEditableField(
                'Duration (minutes)',
                'duration',
                editableData.duration,
                'Enter duration in minutes',
                'numeric'
              )}
              
              {renderEditableField('Location', 'location', editableData.location, 'Enter location')}
            </ScrollView>

            <View style={styles.buttonContainer}>
              <Button
                mode="contained"
                onPress={onDismiss}
                style={[styles.button, styles.cancelButton]}
                labelStyle={styles.cancelButtonLabel}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                mode="contained"
                onPress={handleConfirm}
                style={[styles.button, action === 'delete' ? styles.deleteButton : styles.confirmButton]}
                loading={isLoading}
                disabled={isLoading}
              >
                {action === 'delete' ? 'Delete' : 'Confirm'}
              </Button>
            </View>
          </Card.Content>

          
        </Card>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalCard: {
    width: '100%',
  },
  modalTitle: {
    textAlign: 'center',
    marginBottom: 8,
  },
  modalSubtitle: {
    textAlign: 'center',
    marginBottom: 20,
    color: '#666',
  },
  fieldContainer: {
    marginBottom: 16,
  },
  fieldHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  fieldLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  fieldValue: {
    fontSize: 14,
    color: '#666',
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#f5f5f5',
    borderRadius: 4,
  },
  editButton: {
    margin: 0,
  },
  editContainer: {
    marginTop: 8,
  },
  textInput: {
    backgroundColor: '#fff',
    marginBottom: 8,
  },
  datetimeButtons: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 8,
  },
  datetimeButton: {
    flex: 1,
  },
  editButtons: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 4,
  },
  saveButton: {
    backgroundColor: '#667eea',
    margin: 0,
  },
  cancelButton: {
    backgroundColor: '#be185d',
    margin: 0,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 20,
    gap: 12,
  },
  button: {
    flex: 1,
  },
  confirmButton: {
    backgroundColor: '#667eea',
  },
  deleteButton: {
    backgroundColor: '#be185d',
  },
  cancelButtonLabel: {
    color: '#ffffff',
  },
}); 