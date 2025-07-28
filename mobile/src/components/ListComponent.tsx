import React from 'react';
import {
  View,
  StyleSheet,
} from 'react-native';
import {
  Card,
  Text,
} from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import { Event } from '../models/event';
import { formatDuration, formatLocation } from '../common/formatting';

interface ListComponentProps {
  events: Event[];
}

export default function ListComponent({ events }: ListComponentProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  if (!events || events.length === 0) {
    return null;
  }

  return (
    <View style={styles.container}>
      <View 
      >
        {events.map((event, index) => {
          
          return (
            <Card key={event.id} style={[styles.eventCard, index > 0 && styles.eventCardMargin]}>
              <Card.Content>
                <View style={styles.eventHeader}>
                  <View style={styles.titleContainer}>
                    <Text style={styles.eventTitle} numberOfLines={2}>
                      {event.title}
                    </Text>
                  </View>
                  
                </View>

                <View style={styles.eventDetails}>
                  <View style={styles.detailRow}>
                    <MaterialIcons name="schedule" size={16} color="rgba(255, 255, 255, 0.7)" />
                    <Text style={styles.detailText}>
                      {formatDate(event.startDate)}
                    </Text>
                  </View>

                  <View style={styles.detailRow}>
                    <MaterialIcons name="timer" size={16} color="rgba(255, 255, 255, 0.7)" />
                    <Text style={styles.detailText}>
                      {formatDuration(event.duration)}
                    </Text>
                  </View>

                    <View style={styles.detailRow}>
                      <MaterialIcons name="location-on" size={16} color="rgba(255, 255, 255, 0.7)" />
                      <Text style={styles.detailText} numberOfLines={1}>
                        {formatLocation(event.location)}
                      </Text>
                    </View>
                </View>
              </Card.Content>
            </Card>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
  },
  eventCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  eventCardMargin: {
    marginTop: 8,
  },
  emptyCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    marginTop: 8,
  },
  emptyText: {
    color: 'rgba(255, 255, 255, 0.6)',
    textAlign: 'center',
    fontSize: 14,
  },
  eventHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  titleContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginRight: 8,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: 'white',
    flex: 1,
    lineHeight: 20,
  },
  eventDetails: {
    gap: 8,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  detailText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginLeft: 8,
    flex: 1,
  },
}); 