import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Alert,
} from 'react-native';
import { Text } from 'react-native-paper';
import { Audio } from 'expo-av';
import { MaterialIcons } from '@expo/vector-icons';

interface MicButtonProps {
  onRecordingComplete: (audioUri: string) => void;
  isProcessing?: boolean;
}

export default function MicButton({ 
  onRecordingComplete, 
  isProcessing = false, 
}: MicButtonProps) {
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const scaleAnim = useState(new Animated.Value(1))[0];
  const pulseAnim = useState(new Animated.Value(1))[0];
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const maxRecordingTime = 30;

  useEffect(() => {
    (async () => {
      const { status } = await Audio.requestPermissionsAsync();
      setHasPermission(status === 'granted');
      
      if (status !== 'granted') {
        Alert.alert('Permission required', 'Microphone permission is required to record voice commands.');
      }
    })();
  }, []);

  useEffect(() => {
    if (isRecording) {
      // Start pulse animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.2,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      ).start();

      // Start recording timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          const newTime = prev + 1;
          if (newTime >= maxRecordingTime) {
            // Auto-stop recording when max duration is reached
            stopRecording();
            return 0;
          }
          return newTime;
        });
      }, 1000);
    } else {
      pulseAnim.setValue(1);
      // Clear timer when not recording
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      setRecordingTime(0);
    }
  }, [isRecording, pulseAnim]);

  const startRecording = async () => {
    if (!hasPermission) {
      Alert.alert('Permission required', 'Please grant microphone permission in settings.');
      return;
    }

    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      setRecording(recording);
      setIsRecording(true);
      setRecordingTime(0);
      
      // Scale animation on press
      Animated.spring(scaleAnim, {
        toValue: 0.9,
        useNativeDriver: true,
      }).start();
    } catch (err) {
      console.error('Failed to start recording', err);
      Alert.alert('Error', 'Failed to start recording. Please try again.');
    }
  };
  
  const stopRecording = async () => {
    if (!recording) return;

    try {
      setIsRecording(false);
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      
      // Reset scale animation
      Animated.spring(scaleAnim, {
        toValue: 1,
        useNativeDriver: true,
      }).start();

      if (uri) {
        onRecordingComplete(uri);
      }
    } catch (err) {
      console.error('Failed to stop recording', err);
      Alert.alert('Error', 'Failed to stop recording. Please try again.');
    }
  };

  const handlePressIn = () => {
    if (!isProcessing) {
      startRecording();
    }
  };

  const handlePressOut = () => {
    if (isRecording) {
      stopRecording();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.pulseContainer,
          {
            transform: [{ scale: pulseAnim }],
          },
        ]}
      >
        <TouchableOpacity
          style={[
            styles.micButton,
            isRecording && styles.recording,
            isProcessing && styles.processing,
          ]}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          disabled={isProcessing}
          activeOpacity={0.8}
        >
          <Animated.View
            style={[
              styles.iconContainer,
              {
                transform: [{ scale: scaleAnim }],
              },
            ]}
          >
            <MaterialIcons
              name={isRecording ? 'mic' : 'mic-none'}
              size={40}
              color={isRecording ? '#ff4444' : '#6200ee'}
            />
          </Animated.View>
        </TouchableOpacity>
      </Animated.View>
      
      {isRecording && (
        <Text style={styles.timerText}>
          {formatTime(recordingTime)} / {formatTime(maxRecordingTime)}
        </Text>
      )}
      
      <Text style={styles.instructionText}>
        {isProcessing
          ? 'Processing...'
          : isRecording
          ? 'Release to stop'
          : 'Hold to speak'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  pulseContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  micButton: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  recording: {
    backgroundColor: 'rgba(255, 68, 68, 0.9)',
  },
  processing: {
    backgroundColor: 'rgba(98, 0, 238, 0.6)',
  },
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  instructionText: {
    marginTop: 15,
    fontSize: 16,
    color: 'white',
    fontWeight: '500',
    textAlign: 'center',
  },
  timerText: {
    marginTop: 15,
    fontSize: 16,
    color: 'white',
    fontWeight: '500',
    textAlign: 'center',
  },
}); 