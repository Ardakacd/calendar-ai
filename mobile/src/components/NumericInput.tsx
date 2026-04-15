import React, { forwardRef, useRef, useCallback } from 'react';
import { TextInput as RNTextInput } from 'react-native';
import { TextInput, TextInputProps } from 'react-native-paper';

interface NumericInputProps extends Omit<TextInputProps, 'onChangeText' | 'value'> {
  value: string;
  onValueChange: (value: string) => void;
}

const NumericInput = forwardRef<any, NumericInputProps>(({
  value,
  onValueChange,
  ...props
}, ref) => {
  const innerRef = useRef<RNTextInput>(null);

  const handleChangeText = useCallback((text: string) => {
    const numericText = text.replace(/[^0-9]/g, '');
    // If non-numeric chars were stripped, fix the native input immediately
    if (numericText !== text && innerRef.current) {
      innerRef.current.setNativeProps({ text: numericText });
    }
    onValueChange(numericText);
  }, [onValueChange]);

  return (
    <TextInput
      {...props}
      ref={(node: any) => {
        // Forward both refs
        (innerRef as any).current = node;
        if (typeof ref === 'function') ref(node);
        else if (ref) (ref as any).current = node;
      }}
      defaultValue={value}
      onChangeText={handleChangeText}
      keyboardType="numeric"
    />
  );
});

NumericInput.displayName = 'NumericInput';

export default NumericInput; 