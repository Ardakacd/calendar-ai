import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  TextInput,
  Platform,
  TouchableOpacity,
} from 'react-native';
import { Text, Button, Card, Avatar, IconButton } from 'react-native-paper';
import { LinearGradient } from 'expo-linear-gradient';
import { useNavigation } from '@react-navigation/native';

import MicButton from '../components/MicButton';
import ListComponent from '../components/ListComponent';
import DeleteComponent from '../components/DeleteComponent';
import CreateComponent from '../components/CreateComponent';
import UpdateComponent from '../components/UpdateComponent';
import { useCalendarAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Event, EventCreate } from '../models/event';

// Animated thinking dots component
const ThinkingDots = () => {
  const [dots, setDots] = useState('');

  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '';
        if (prev === '..') return '...';
        if (prev === '.') return '..';
        return '.';
      });
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return <Text style={{ fontSize: 16, lineHeight: 22, color: 'rgba(255, 255, 255, 0.9)' }}>{dots}</Text>;
};

interface ChatMessage {
  id: string;
  type: 'user' | 'ai';
  content: string;
  timestamp: Date;
  eventData?: EventCreate;
  events?: Event[];
  updateArguments?: any;
  responseType?: 'text' | 'list' | 'delete' | 'create' | 'update';
}

export default function HomeScreen() {
  const navigation = useNavigation();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: Date.now().toString(),
      type: 'ai',
      content: 'Merhaba, bugün size nasıl yardımcı olabilirim?',
      timestamp: new Date(),
      eventData: undefined,
      events: undefined,
      responseType: 'text',
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [hasUncompletedComponent, setHasUncompletedComponent] = useState(false);
  const { transcribeAudio, addEvent, processText, deleteMultipleEvents, updateEvent } = useCalendarAPI();
  const { user, logout } = useAuth();
  const scrollViewRef = useRef<ScrollView>(null);
  const inputRef = useRef<TextInput>(null);
  

  const addMessage = (type: 'user' | 'ai', content: string, eventData?: EventCreate, events?: Event[], responseType: 'text' | 'list' | 'delete' | 'create' | 'update' = 'text', updateArguments?: any) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      type,
      content: content ? content.trim() : '',
      timestamp: new Date(),
      eventData,
      events,
      updateArguments,
      responseType,
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage = inputText.trim();
    addMessage('user', userMessage);
    setInputText('');
    scrollToBottom();
    await handleProcessText(userMessage)

    // Maintain focus on the input
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);

  };

  const handleProcessText = async (text: string) => {
    setIsThinking(true);
    try {
      const response = await processText(text)
    
      if (response && typeof response === 'object' && response.type === 'list' && response.events) {
        addMessage('ai', response.message || 'İşte etkinlikleriniz:', undefined, response.events, 'list')
      } else if (response && typeof response === 'object' && response.type === 'delete' && response.events) {
        addMessage('ai', response.message || 'Silinecek etkinlikleri seçin:', undefined, response.events, 'delete')
        setHasUncompletedComponent(true);
      } else if (response && typeof response === 'object' && response.type === 'create' && response.event) {
        addMessage('ai', response.message || 'Lütfen etkinlik detaylarını gözden geçirin:', response.event, undefined, 'create')
        setHasUncompletedComponent(true);
      } else if (response && typeof response === 'object' && response.type === 'update' && response.events) {
        addMessage('ai', response.message || 'Güncellenecek etkinlikleri seçin:', undefined, response.events, 'update', response.update_arguments)
        setHasUncompletedComponent(true);
      } else {
        // Handle string responses or other types
        const message = typeof response === 'string' ? response : (response?.message || 'Komut başarıyla işlendi.');
        addMessage('ai', message, undefined, undefined, 'text')
      }
      
      scrollToBottom();
    } catch (error) {
      addMessage('ai', 'Üzgünüm, komutunuzu işleyemedim. Lütfen tekrar deneyin.');
      scrollToBottom();
    } finally {
      setIsThinking(false);
    }
  }

  const handleVoiceCommand = async (audioUri: string) => {
    setIsProcessing(true);

    try {
      const response = await transcribeAudio(audioUri);
      const userMessage = response.message || 'Ses komutu işlendi';
      addMessage('user', userMessage);
      scrollToBottom();
      await handleProcessText(userMessage)

      //await processCommand(userMessage);
    } catch (error) {
      console.error('Error processing voice command:', error);
      addMessage('ai', 'Üzgünüm, ses komutunuzu işleyemedim. Lütfen tekrar deneyin.');
      scrollToBottom();
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeleteEvent = async (eventIds: string[]) => {
    try {
      const response = await deleteMultipleEvents(eventIds);
      addMessage('ai', response.message || 'Etkinlikler basariyla silindi!', undefined, undefined, 'text');
      scrollToBottom();
    } catch (error) {
      addMessage('ai', 'Etkinlikler silinemedi. Lütfen tekrar deneyin.', undefined, undefined, 'text');
      scrollToBottom();
    }
  };

  const handleCreateEvent = async (eventData: EventCreate) => {
    try {
      await addEvent(eventData, false);
      addMessage('ai', 'Etkinlik başarıyla oluşturuldu!', undefined, undefined, 'text');
      scrollToBottom();
    } catch (error) {
      addMessage('ai', 'Etkinlik oluşturulamadı. Lütfen tekrar deneyin.', undefined, undefined, 'text');
      scrollToBottom();
    }
  };

  const handleUpdateEvent = async (eventId: string, updatedEvent: any) => {
    try {
      await updateEvent(eventId, updatedEvent);
      addMessage('ai', 'Etkinlik başarıyla güncellendi!', undefined, undefined, 'text');
      scrollToBottom();
    } catch (error) {
      addMessage('ai', 'Etkinlik güncellenemedi. Lütfen tekrar deneyin.', undefined, undefined, 'text');
      scrollToBottom();
    }
  };

  // Function to mark component as completed
  const markComponentAsCompleted = () => {
    setHasUncompletedComponent(false);
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.type === 'user';

    return (
      <View key={message.id} style={[styles.messageContainer, isUser ? styles.userMessage : styles.aiMessage]}>
        <View style={[styles.messageBubble, isUser ? styles.userBubble : styles.aiBubble]}>
          <Text style={[styles.messageText, isUser ? styles.userMessageText : styles.aiMessageText]}>
            {message.content}
          </Text>

          {message.responseType === 'list' && message.events && (
            <ListComponent 
              events={message.events} 
            />
          )}

          {message.responseType === 'delete' && message.events && (
            <DeleteComponent 
              events={message.events}
              onDelete={handleDeleteEvent}
              onCompleted={markComponentAsCompleted}
            />
          )}

          {message.responseType === 'create' && message.eventData && (
            <CreateComponent 
              eventData={message.eventData}
              onCreate={handleCreateEvent}
              onCompleted={markComponentAsCompleted}
            />
          )}

          {message.responseType === 'update' && message.events && (
            <UpdateComponent 
              events={message.events}
              updateArguments={message.updateArguments || {}}
              onUpdate={handleUpdateEvent}
              onCompleted={markComponentAsCompleted}
            />
          )}

        </View>
      </View>
    );
  };

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.navigate('Profile' as never)}>
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
        </TouchableOpacity>
        <IconButton
          icon="calendar"
          iconColor="white"
          size={24}
          onPress={() => navigation.navigate('Calendar' as never)}
          style={styles.logoutButton}
        />
      </View>

      <KeyboardAvoidingView
        style={styles.chatContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.map(renderMessage)}
          {isThinking && (
            <View style={[styles.messageContainer, styles.aiMessage]}>
              <View style={[styles.messageBubble, styles.aiBubble]}>
                <ThinkingDots />
              </View>
            </View>
          )}
        </ScrollView>

        <View style={styles.inputContainer}>
          <TextInput
            value={inputText}
            onChangeText={setInputText}
            placeholder="Komutunuzu yazın..."
            placeholderTextColor="rgba(255, 255, 255, 0.6)"
            onSubmitEditing={handleSendMessage}
            returnKeyType="send"
            style={[styles.textInput, hasUncompletedComponent && styles.disabledInput]}
            contextMenuHidden={true}
            selectTextOnFocus={false}
            autoCorrect={false}
            autoCapitalize="none"
            editable={!hasUncompletedComponent}
            pointerEvents={hasUncompletedComponent ? "none" : "auto"}
            ref={inputRef}
          />
          <View>
            {inputText.trim() ? (
              <IconButton
                icon="send"
                iconColor="white"
                size={20}
                onPress={handleSendMessage}
                style={[styles.sendButton, hasUncompletedComponent && styles.disabledButton]}
                disabled={hasUncompletedComponent}
              />
            ) : (
              <MicButton
                onRecordingComplete={handleVoiceCommand}
                isProcessing={isProcessing}
                disabled={hasUncompletedComponent}
              />
            )}
          </View>
        </View>
      </KeyboardAvoidingView>

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
    paddingTop: 80,
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
  logoutButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    marginLeft: 10,
  },
  chatContainer: {
    flex: 1,
    borderTopWidth:3,
    borderTopColor:'rgba(255, 255, 255, 0.1)',
    paddingTop: 12
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    paddingHorizontal: 8,
    paddingBottom: 20,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop:20,
    paddingBottom: 32,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
    gap: 8
  },
  textInput: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderBottomLeftRadius: 18,
    borderBottomRightRadius: 18,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 14,
    color: 'white',
    borderWidth: 0,
    borderColor: 'transparent',
  },
  disabledInput: {
    opacity: 0.5,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  inputButtons: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sendButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 20,
    width: 40,
    height: 40,
    margin: 0,
    padding:0
  },
  disabledButton: {
    opacity: 0.5,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  messageContainer: {
    marginVertical: 8,
    paddingHorizontal: 8,
  },
  userMessage: {
    alignItems: 'flex-end',
  },
  aiMessage: {
    alignItems: 'flex-start',
  },
  messageBubble: {
    maxWidth: '90%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  userBubble: {
    backgroundColor: '#667eea',
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userMessageText: {
    color: 'white',
  },
  aiMessageText: {
    color: 'rgba(255, 255, 255, 0.9)',
  },
  eventCard: {
    marginTop: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: 'white',
  },
  eventDetail: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginBottom: 4,
  },
}); 