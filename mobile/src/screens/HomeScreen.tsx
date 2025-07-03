import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import { Text, Button, Card, Avatar, IconButton } from 'react-native-paper';
import { LinearGradient } from 'expo-linear-gradient';
import { useNavigation } from '@react-navigation/native';

import MicButton from '../components/MicButton';
import AssistantFeedback from '../components/AssistantFeedback';
import ConfirmationModal from '../components/ConfirmationModal';
import { useCalendarAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface EventConfirmationData {
  title: string;
  datetime: string;
  duration?: number;
  location?: string;
}

export default function HomeScreen() {
  const navigation = useNavigation();
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [confirmationData, setConfirmationData] = useState<{
    action: 'create' | 'update' | 'delete';
    eventData: EventConfirmationData;
  } | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const { transcribeAudio, confirmAction } = useCalendarAPI();
  const { user, logout } = useAuth();

  const handleVoiceCommand = async (audioUri: string) => {
    setIsProcessing(true);
    setFeedback(null);
    
    try {
      const response = await transcribeAudio(audioUri);
      console.log('response');  
      console.log(response);
      setFeedback(response.message);

      // Check if confirmation is required
      if (response.requires_confirmation && response.confirmation_data) {
        setConfirmationData({
          action: response.action as 'create' | 'update' | 'delete',
          eventData: response.confirmation_data,
        });
        setShowConfirmationModal(true);
        
      } else {
        // For queries or other actions that don't require confirmation
        if (response.action === 'create' || response.action === 'delete' || response.action === 'update') {
          setTimeout(() => {
            navigation.navigate('Calendar' as never);
          }, 2000);
        }
      }
    } catch (error) {
      console.error('Error processing voice command:', error);
      Alert.alert('Error', 'Failed to process voice command. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmAction = async (eventData: EventConfirmationData) => {
    if (!confirmationData) return;
    
    setIsConfirming(true);
    try {
      console.log('eventData');
      console.log(eventData);
      const result = await confirmAction({
        action: confirmationData.action,
        event_data: eventData,
      });
      
      setFeedback(result.message);
      setShowConfirmationModal(false);
      setConfirmationData(null);
      
      // Navigate to calendar after successful action
      setTimeout(() => {
        navigation.navigate('Calendar' as never);
      }, 2000);
      
    } catch (error) {
      console.error('Error confirming action:', error);
      Alert.alert('Error', 'Failed to confirm action. Please try again.');
    } finally {
      setIsConfirming(false);
    }
  };

  const handleDismissModal = () => {
    setShowConfirmationModal(false);
    setConfirmationData(null);
  };

  const handleLogout = async () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            try {
              await logout();
            } catch (error) {
              console.error('Logout error:', error);
            }
          },
        },
      ]
    );
  };

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <View style={styles.header}>
        <View style={styles.userInfo}>
          <Avatar.Text 
            size={40} 
            label={user?.name?.charAt(0)?.toUpperCase() || 'U'} 
            style={styles.avatar}
          />
          <View style={styles.userText}>
            <Text style={styles.userName}>{user?.name || 'User'}</Text>
          </View>
        </View>
        <IconButton
          icon="logout"
          iconColor="white"
          size={24}
          onPress={handleLogout}
          style={styles.logoutButton}
        />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.titleContainer}>
          <Text style={styles.title}>Calendar AI</Text>
          <Text style={styles.subtitle}>Your voice-powered calendar assistant</Text>
        </View>

        <Card style={styles.instructionCard}>
          <Card.Content>
            <Text style={styles.instructionTitle}>How to use:</Text>
            <Text style={styles.instructionText}>
              • "Add a meeting with Sarah next Thursday at 4 PM"{'\n'}
              • "Delete my lunch with John tomorrow"{'\n'}
              • "Schedule a call with Alex on Friday at 2 PM"{'\n'}
              • "What's on my calendar today?"
            </Text>
          </Card.Content>
        </Card>

        <View style={styles.micContainer}>
          <MicButton
            onRecordingComplete={handleVoiceCommand}
            isProcessing={isProcessing}
          />
          {isProcessing && (
            <Text style={styles.processingText}>Processing your command...</Text>
          )}
        </View>

        {feedback && (
          <AssistantFeedback message={feedback} />
        )}

        <View style={styles.buttonContainer}>
          <Button
            mode="contained"
            onPress={() => navigation.navigate('Calendar' as never)}
            style={styles.button}
            labelStyle={styles.buttonLabel}
          >
            View Calendar
          </Button>
        </View>
      </ScrollView>

      {confirmationData && (
        <ConfirmationModal
          visible={showConfirmationModal}
          onDismiss={handleDismissModal}
          action={confirmationData.action}
          eventData={confirmationData.eventData}
          onConfirm={handleConfirmAction}
          isLoading={isConfirming}
        />
      )}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 50,
    paddingBottom: 20,
  },
  userInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  avatar: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    marginRight: 12,
  },
  userText: {
    flex: 1,
  },
  userName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: 'white',
  },
  userEmail: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  logoutButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    marginLeft: 10,
  },
  scrollContent: {
    flexGrow: 1,
    padding: 20,
    alignItems: 'center',
  },
  titleContainer: {
    alignItems: 'center',
    marginBottom: 30,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
    textAlign: 'center',
  },
  instructionCard: {
    width: '100%',
    marginBottom: 30,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
  },
  instructionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
  },
  instructionText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#666',
  },
  micContainer: {
    alignItems: 'center',
    marginVertical: 30,
  },
  processingText: {
    color: 'white',
    fontSize: 16,
    marginTop: 15,
    fontWeight: '500',
  },
  buttonContainer: {
    width: '100%',
    marginTop: 20,
  },
  button: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  buttonLabel: {
    fontSize: 16,
    fontWeight: '600',
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
    backgroundColor: '#6200ee',
  },
}); 