import React, { useState, useEffect, useRef, useCallback } from 'react';
import { View, StyleSheet, TouchableOpacity, Animated } from 'react-native';
import { Text } from 'react-native-paper';
import { useAudioRecorder, RecordingPresets, requestRecordingPermissionsAsync } from 'expo-audio';
import { MaterialIcons } from '@expo/vector-icons';
import { showErrorToast } from '../common/toast/toast-message';
import { Colors, Radius } from '../theme';

interface MicButtonProps {
  onRecordingComplete: (audioUri: string) => void;
  isProcessing?: boolean;
  disabled?: boolean;
}

export default function MicButton({ onRecordingComplete, isProcessing = false, disabled = false }: MicButtonProps) {
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
      Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true }).start();
      if (uri) onRecordingComplete(uri);
    } catch {
      showErrorToast('Recording could not be stopped. Please try again.');
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
      if (!granted) showErrorToast('Microphone permission is required for voice commands.');
    })();
  }, []);

  useEffect(() => {
    if (isRecording) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.15, duration: 700, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 700, useNativeDriver: true }),
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
      showErrorToast('Microphone permission is required for voice commands.');
      return;
    }
    try {
      recorder.record();
      setIsRecording(true);
      setRecordingTime(0);
      Animated.spring(scaleAnim, { toValue: 0.9, useNativeDriver: true }).start();
    } catch {
      showErrorToast('Recording could not be started. Please try again.');
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getButtonStyle = () => {
    if (isRecording) return [styles.btn, styles.btnRecording];
    if (isProcessing) return [styles.btn, styles.btnProcessing];
    if (disabled) return [styles.btn, styles.btnDisabled];
    return styles.btn;
  };

  const getIconColor = () => {
    if (isRecording) return '#FFFFFF';
    if (isProcessing) return Colors.surface;
    return Colors.primary;
  };

  return (
    <View style={styles.container}>
      <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
        <TouchableOpacity
          style={getButtonStyle()}
          onPressIn={() => { if (!isProcessing) startRecording(); }}
          onPressOut={() => { if (isRecording) stopRecording(); }}
          disabled={isProcessing || disabled}
          activeOpacity={0.8}
        >
          <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
            <MaterialIcons
              name={isRecording ? 'mic' : 'mic-none'}
              size={22}
              color={getIconColor()}
            />
          </Animated.View>
        </TouchableOpacity>
      </Animated.View>
      {isRecording && (
        <Text style={styles.timerText}>{formatTime(recordingTime)}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  btn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  btnRecording: {
    backgroundColor: Colors.error,
    borderColor: Colors.error,
  },
  btnProcessing: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
    opacity: 0.7,
  },
  btnDisabled: {
    opacity: 0.4,
  },
  timerText: {
    fontSize: 11,
    color: Colors.textSecondary,
    fontWeight: '500',
    marginTop: 4,
  },
});
