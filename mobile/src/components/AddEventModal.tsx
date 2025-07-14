import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import {
  Modal,
  Portal,
  Text,
  TextInput,
  Button,
  Card,
  Title,
} from 'react-native-paper';
import DateTimePicker from '@react-native-community/datetimepicker';
import { MaterialIcons } from '@expo/vector-icons';
import NumericInput from './NumericInput';
import { EventCreate } from '../models/event';

interface AddEventModalProps {
  visible: boolean;
  onDismiss: () => void;
  onAdd: (event: EventCreate) => Promise<void>;
  onEdit?: (event: EventCreate) => Promise<void>;
  initialEvent?: EventCreate;
  mode?: 'add' | 'edit';
}

export default function AddEventModal({
  visible,
  onDismiss,
  onAdd,
  onEdit,
  initialEvent,
  mode = 'add',
}: AddEventModalProps) {
  const [title, setTitle] = useState('');
  const [location, setLocation] = useState('');
  const [duration, setDuration] = useState('');
  const [datetime, setDatetime] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [loading, setLoading] = useState(false);

  // Initialize form with initial values when editing
  useEffect(() => {
    if (initialEvent && mode === 'edit') {
      setTitle(initialEvent.title);
      setLocation(initialEvent.location || '');
      setDuration(initialEvent.duration ? initialEvent.duration.toString() : '');
      setDatetime(new Date(initialEvent.startDate));
    } else {
      // Reset form for add mode
      setTitle('');
      setLocation('');
      setDuration('');
      setDatetime(new Date());
    }
  }, [initialEvent, mode, visible]);

  const handleSubmit = async () => {
    if (!title.trim()) {
      Alert.alert('Hata', 'Başlık gereklidir');
      return;
    }

    // Duration is optional, but if provided, it must be valid
    let durationMinutes: number | undefined;
    if (duration) {
      durationMinutes = parseInt(duration);
      if (durationMinutes <= 0) {
        Alert.alert('Hata', 'Süre 0\'dan büyük olmalıdır');
        return;
      }
    }

    const eventData: EventCreate = {
      title: title.trim(),
      location: location.trim() || undefined,
      duration: durationMinutes,
      startDate: datetime.toISOString(),
    };

    try {
      setLoading(true);
      
      if (mode === 'edit' && onEdit && initialEvent) {
        await onEdit(eventData);
      } else {
        await onAdd(eventData);
        Alert.alert('Başarılı', 'Etkinlik başarıyla eklendi');
      }
      
      // Reset form
      setTitle('');
      setLocation('');
      setDuration('');
      setDatetime(new Date());
      
      onDismiss();
    } catch (error) {
      console.error('Error saving event:', error);
      Alert.alert('Hata', mode === 'edit' ? 'Etkinlik güncellenemedi' : 'Etkinlik eklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const onDateChange = (event: any, selectedDate?: Date) => {
    setShowDatePicker(false);
    if (selectedDate) {
      setDatetime(selectedDate);
    }
  };

  const formatDateTime = (date: Date) => {
    return date.toLocaleString();
  };

  return (
    <Portal>
      <Modal
        visible={visible}
        onDismiss={onDismiss}
        contentContainerStyle={styles.modalContainer}
      >
        <Card>
          <Card.Content>
            <Title style={styles.title}>
              {mode === 'edit' ? 'Etkinlik Düzenle' : 'Yeni Etkinlik Ekle'}
            </Title>
            
            <ScrollView>
              <View style={styles.inputContainer}>
                <Text style={styles.label}>Başlık *</Text>
                <TextInput
                  mode="outlined"
                  value={title}
                  onChangeText={setTitle}
                  placeholder="Etkinlik başlığını girin"
                  style={styles.input}
                />
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>Tarih & Saat *</Text>
                <Button
                  mode="outlined"
                  onPress={() => setShowDatePicker(true)}
                  style={styles.dateButton}
                  icon="calendar-clock"
                >
                  {formatDateTime(datetime)}
                </Button>
                {showDatePicker && (
                  <DateTimePicker
                    value={datetime}
                    mode="datetime"
                    display="default"
                    onChange={onDateChange}
                  />
                )}
              </View>

              <View style={styles.inputContainer}>
                <View style={styles.labelContainer}>
                  <MaterialIcons name="schedule" size={20} color="#6200ee" />
                  <Text style={styles.label}>Süre (dakika)</Text>
                </View>
                <NumericInput
                  mode="outlined"
                  value={duration}
                  onValueChange={setDuration}
                  placeholder="Dakika cinsinden süre giriniz"
                  style={styles.input}
                />
                <Text style={styles.helperText}>
                  Süre dakika cinsinden giriniz (örn: 30 dakika) - Opsiyonel
                </Text>
              </View>

              <View style={styles.inputContainer}>
                <View style={styles.labelContainer}>
                  <MaterialIcons name="location-on" size={20} color="#6200ee" />
                  <Text style={styles.label}>Konum</Text>
                </View>
                <TextInput
                  mode="outlined"
                  value={location}
                  onChangeText={setLocation}
                  placeholder="Etkinlik konumunu girin (opsiyonel)"
                  style={styles.input}
                />
              </View>
            </ScrollView>

            <View style={styles.buttonContainer}>
              <Button
                mode="outlined"
                onPress={onDismiss}
                style={[styles.button, styles.cancelButton]}
                disabled={loading}
              >
                İptal Et
              </Button>
              <Button
                mode="contained"
                onPress={handleSubmit}
                style={[styles.button, styles.addButton]}
                loading={loading}
                disabled={loading}
              >
                {mode === 'edit' ? 'Etkinlik Güncelle' : 'Etkinlik Ekle'}
              </Button>
            </View>
          </Card.Content>
        </Card>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  title: {
    textAlign: 'center',
    marginBottom: 20,
    color: '#1a1a1a',
    fontSize: 22,
    fontWeight: 'bold',
  },
  inputContainer: {
    marginBottom: 16,
  },
  labelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginLeft: 8,
  },
  input: {
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
  },
  dateButton: {
    marginTop: 4,
    borderRadius: 12,
    borderColor: '#6200ee',
    borderWidth: 1.5,
  },
  helperText: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    fontStyle: 'italic',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 20,
    gap: 12,
  },
  button: {
    flex: 1,
    borderRadius: 12,
    elevation: 2,
  },
  cancelButton: {
    borderColor: '#6200ee',
    borderWidth: 1.5,
  },
  addButton: {
    backgroundColor: '#6200ee',
  },
}); 