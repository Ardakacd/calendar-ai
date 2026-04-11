import React, { useState, useEffect } from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createStackNavigator} from '@react-navigation/stack';
import {Provider as PaperProvider} from 'react-native-paper';
import {StatusBar} from 'expo-status-bar';
import {GestureHandlerRootView} from 'react-native-gesture-handler';
import {ActivityIndicator, StyleSheet, View} from 'react-native';

import {AuthProvider, useAuth} from './src/contexts/AuthContext';
import { registerForPushNotifications } from './src/services/notifications';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import CalendarScreen from './src/screens/CalendarScreen';
import SignupScreen from './src/screens/SignupScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import Toast from 'react-native-toast-message';
import {toastConfig} from './src/common/toast/ToastConfig';
import 'intl';
import 'intl/locale-data/jsonp/en';

const Stack = createStackNavigator();

const AppContent: React.FC = () => {
    const {isAuthenticated, isLoading} = useAuth();
    const [showSignup, setShowSignup] = useState(false);

    useEffect(() => {
        if (isAuthenticated) {
            registerForPushNotifications();
        }
    }, [isAuthenticated]);

    if (isLoading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#6200ee"/>
            </View>
        );
    }

    // If not authenticated, show auth screens without navigation stack
    if (!isAuthenticated) {
        return (
            <View style={{ flex: 1 }}>
                <StatusBar style="auto"/>
                {showSignup ? (
                    <SignupScreen setShowSignup={setShowSignup} />
                ) : (
                    <LoginScreen setShowSignup={setShowSignup} />
                )}
            </View>
        );
    }

    // If authenticated, show main app with navigation
    return (
        <NavigationContainer>
            <StatusBar style="auto"/>
            <Stack.Navigator
                screenOptions={{
                    headerStyle: {
                        backgroundColor: '#FFFFFF',
                        elevation: 0,
                        shadowColor: '#000',
                        shadowOffset: { width: 0, height: 1 },
                        shadowOpacity: 0.06,
                        shadowRadius: 4,
                        borderBottomWidth: 1,
                        borderBottomColor: '#E5E7EB',
                    },
                    headerTintColor: '#6366F1',
                    headerTitleStyle: {
                        fontWeight: '600',
                        color: '#111827',
                        fontSize: 17,
                    },
                }}
            >
                <Stack.Screen
                    name="Home"
                    component={HomeScreen}
                    options={{headerShown: false}}
                />
                <Stack.Screen
                    name="Calendar"
                    component={CalendarScreen}
                    options={{title: 'Calendar'}}
                />
                <Stack.Screen
                    name="Profile"
                    component={ProfileScreen}
                    options={{title: 'Profile'}}
                />
            </Stack.Navigator>
        </NavigationContainer>
    );
};

export default function App() {
    return (
        <GestureHandlerRootView style={{flex: 1}}>
            <PaperProvider>
                <AuthProvider>
                    <AppContent/>
                </AuthProvider>
            </PaperProvider>
            <Toast config={toastConfig} />
        </GestureHandlerRootView>
    );
}

const styles = StyleSheet.create({
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#FFFFFF',
    },
}); 