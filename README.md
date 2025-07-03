# Calendar AI - Voice-Powered Calendar Assistant

An AI-powered personal calendar assistant that lets users manage their schedule using just their voice. Built with React Native and FastAPI.

## 🚀 Features

- **🎙️ Push-to-Talk Interface**: Hold the mic button to record voice commands
- **🗓️ In-App Calendar**: Beautiful calendar view with event management
- **🤖 AI Processing**: Natural language processing for calendar commands
- **🔒 Privacy-Focused**: No external calendar services required
- **📱 Cross-Platform**: Works on iOS and Android

## 📱 Voice Commands

The app understands natural language commands like:

- "Add a meeting with Sarah next Thursday at 4 PM"
- "Delete my lunch with John tomorrow"
- "Schedule a call with Alex on Friday at 2 PM"
- "What's on my calendar today?"

## 🏗️ Architecture

### Frontend (React Native + Expo)
- **HomeScreen**: Main interface with push-to-talk button
- **CalendarScreen**: Calendar view with event display
- **EventListScreen**: List view with search functionality
- **Components**: Reusable UI components
- **Services**: API integration layer

### Backend (FastAPI)
- **Speech-to-Text**: Audio transcription using Google Speech Recognition
- **AI Processor**: Natural language processing for calendar commands
- **Database**: SQLite for event storage
- **REST API**: Full CRUD operations for events

## 🛠️ Setup Instructions

### Prerequisites
- Node.js (v16 or higher)
- Python (v3.10 or higher)
- Expo CLI
- iOS Simulator or Android Emulator (for testing)

### Frontend Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm start
   ```

3. **Run on device/simulator**:
   ```bash
   # iOS
   npm run ios
   
   # Android
   npm run android
   ```

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Environment Configuration

Create a `.env` file in the backend directory:
```env
# Optional: OpenAI API key for enhanced AI processing
OPENAI_API_KEY=your_openai_api_key_here
```
## 🔮 Future Enhancements

- [ ] Multi-day event support
- [ ] Recurring events
- [ ] Local notifications
- [ ] Dark/light theme toggle
- [ ] Event categories and colors
- [ ] Voice reminders
- [ ] Calendar sharing
- [ ] Offline support

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**Audio recording not working**:
- Check microphone permissions in device settings
- Ensure the app has audio recording permissions

**Backend connection failed**:
- Verify the backend server is running on port 8000
- Check if the API_BASE_URL in `src/services/api.ts` is correct

**Speech recognition issues**:
- Ensure stable internet connection
- Check audio quality and background noise
- Try speaking more clearly and slowly

### Development Tips

- Use Expo Go app for quick testing on physical devices
- Enable hot reloading for faster development
- Use React Native Debugger for debugging
- Check the FastAPI docs at `http://localhost:8000/docs`

## 📞 Support

For support and questions, please open an issue on GitHub or contact the development team. 