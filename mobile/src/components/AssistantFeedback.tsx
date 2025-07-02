import React, { useEffect, useState } from 'react';
import {
  View,
  StyleSheet,
  Animated,
} from 'react-native';
import { Card, Text, IconButton } from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';

interface AssistantFeedbackProps {
  message: string;
  type?: 'success' | 'error' | 'info';
}

export default function AssistantFeedback({ message, type = 'info' }: AssistantFeedbackProps) {
  const [fadeAnim] = useState(new Animated.Value(0));
  const [slideAnim] = useState(new Animated.Value(50));

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        tension: 100,
        friction: 8,
        useNativeDriver: true,
      }),
    ]).start();
  }, [fadeAnim, slideAnim]);

  const getIcon = () => {
    switch (type) {
      case 'success':
        return 'check-circle';
      case 'error':
        return 'error';
      default:
        return 'info';
    }
  };

  const getColor = () => {
    switch (type) {
      case 'success':
        return '#4caf50';
      case 'error':
        return '#f44336';
      default:
        return '#2196f3';
    }
  };

  return (
    <Animated.View
      style={[
        styles.container,
        {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }],
        },
      ]}
    >
      <Card style={[styles.card, { borderLeftColor: getColor() }]}>
        <Card.Content style={styles.content}>
          <MaterialIcons
            name={getIcon()}
            size={24}
            color={getColor()}
            style={styles.icon}
          />
          <Text style={styles.message}>{message}</Text>
        </Card.Content>
      </Card>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    marginVertical: 10,
  },
  card: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  icon: {
    marginRight: 12,
  },
  message: {
    flex: 1,
    fontSize: 16,
    lineHeight: 22,
    color: '#333',
  },
}); 