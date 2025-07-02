import React, { forwardRef } from 'react';
import { TextInput, TextInputProps } from 'react-native-paper';

interface NumericInputProps extends Omit<TextInputProps, 'onChangeText'> {
  value: string;
  onValueChange: (value: string) => void;
}

const NumericInput = forwardRef<any, NumericInputProps>(({ 
  value, 
  onValueChange, 
  ...props 
}, ref) => {
  const handleChangeText = (text: string) => {
    // Only allow numeric characters
    const numericText = text.replace(/[^0-9]/g, '');
    onValueChange(numericText);
  };

  return (
    <TextInput
      {...props}
      ref={ref}
      value={value}
      onChangeText={handleChangeText}
      keyboardType="numeric"
    />
  );
});

NumericInput.displayName = 'NumericInput';

export default NumericInput; 