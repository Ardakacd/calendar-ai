import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  disabled?: boolean;
}

export default function MicButton({ 
  onRecordingComplete, 
  isProcessing = false, 
  disabled = false,
}: MicButtonProps) {
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const scaleAnim = useState(new Animated.Value(1))[0];
  const pulseAnim = useState(new Animated.Value(1))[0];
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const maxRecordingTime = 30;

  const updateTimer = useCallback(() => {
    setRecordingTime(prev => {
      const newTime = prev + 1;
      if (newTime >= maxRecordingTime) {
        // Auto-stop recording when max duration is reached
        setTimeout(() => {
          if (recording) {
            stopRecording();
          }
        }, 0);
        return 0;
      }
      return newTime;
    });
  }, [maxRecordingTime, recording]);

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
      recordingTimerRef.current = setInterval(updateTimer, 1000);
    } else {
      pulseAnim.setValue(1);
      // Clear timer when not recording
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      setRecordingTime(0);
    }
  }, [isRecording, pulseAnim, updateTimer]);

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
            disabled && styles.disabled,
          ]}
          onPressIn={handlePressIn}
          onPressOut={handlePressOut}
          disabled={isProcessing || disabled}
          activeOpacity={0.8}
        >
          <Animated.View
            style={[
              {
                transform: [{ scale: scaleAnim }],
              },
            ]}
          >
            <MaterialIcons
              name={isRecording ? 'mic' : 'mic-none'}
              size={24}
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  micButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  recording: {
    backgroundColor: 'rgba(255, 68, 68, 0.9)',
  },
  processing: {
    backgroundColor: 'rgba(98, 0, 238, 0.6)',
  },
  disabled: {
    opacity: 0.5,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
  },
  instructionText: {
    marginTop: 15,
    fontSize: 16,
    color: 'white',
    fontWeight: '500',
    textAlign: 'center',
  },
  timerText: {
    fontSize: 12,
    color: 'white',
    fontWeight: '500',
    textAlign: 'center',
    minWidth:80,
    marginTop:4
  },
}); 