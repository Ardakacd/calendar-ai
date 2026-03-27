import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Animated,
} from 'react-native';
import { Text } from 'react-native-paper';
import { useAudioRecorder, RecordingPresets, requestRecordingPermissionsAsync } from 'expo-audio';
import { MaterialIcons } from '@expo/vector-icons';
import { showErrorToast } from '../common/toast/toast-message';

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
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [isRecording, setIsRecording] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const scaleAnim = useState(new Animated.Value(1))[0];
  const pulseAnim = useState(new Animated.Value(1))[0];
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const maxRecordingTime = 30;

  const stopRecording = useCallback(async () => {
    try {
      setIsRecording(false);
      await recorder.stop();
      const uri = recorder.uri;

      Animated.spring(scaleAnim, {
        toValue: 1,
        useNativeDriver: true,
      }).start();

      if (uri) {
        onRecordingComplete(uri);
      }
    } catch (err) {
      showErrorToast('Kayıt durdurulamadı. Lütfen tekrar deneyin.');
    }
  }, [recorder, scaleAnim, onRecordingComplete]);

  const updateTimer = useCallback(() => {
    setRecordingTime(prev => {
      const newTime = prev + 1;
      if (newTime >= maxRecordingTime) {
        setTimeout(() => stopRecording(), 0);
        return 0;
      }
      return newTime;
    });
  }, [maxRecordingTime, stopRecording]);

  useEffect(() => {
    (async () => {
      const { granted } = await requestRecordingPermissionsAsync();
      setHasPermission(granted);
      if (!granted) {
        showErrorToast('Ses komutları kaydetmek için mikrofon izni gereklidir.');
      }
    })();
  }, []);

  useEffect(() => {
    if (isRecording) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.2, duration: 800, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 800, useNativeDriver: true }),
        ])
      ).start();
      recordingTimerRef.current = setInterval(updateTimer, 1000);
    } else {
      pulseAnim.setValue(1);
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      setRecordingTime(0);
    }
  }, [isRecording, pulseAnim, updateTimer]);

  const startRecording = async () => {
    if (!hasPermission) {
      showErrorToast('Ses komutları kaydetmek için mikrofon izni gereklidir.');
      return;
    }
    try {
      recorder.record();
      setIsRecording(true);
      setRecordingTime(0);
      Animated.spring(scaleAnim, { toValue: 0.9, useNativeDriver: true }).start();
    } catch (err) {
      showErrorToast('Kayıt başlatılamadı. Lütfen tekrar deneyin.');
    }
  };

  const handlePressIn = () => {
    if (!isProcessing) startRecording();
  };

  const handlePressOut = () => {
    if (isRecording) stopRecording();
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <View style={styles.container}>
      <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
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
          <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
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
    shadowOffset: { width: 0, height: 2 },
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
  timerText: {
    fontSize: 12,
    color: 'white',
    fontWeight: '500',
    textAlign: 'center',
    minWidth: 80,
    marginTop: 4,
  },
});
