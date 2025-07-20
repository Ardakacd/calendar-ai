import React from "react";
import {
  BaseToast,
  BaseToastProps,
  ToastConfig,
} from "react-native-toast-message";

export const toastProps: BaseToastProps = {
  text1NumberOfLines: 0,
  style: {
    height: "auto",
    paddingVertical: 12,
    paddingHorizontal: 12,
  },
};

export const toastConfig: ToastConfig = {
  success: (props) => (
    <BaseToast
      {...props}
      {...toastProps}
      style={[
        toastProps.style,
        {
          borderLeftColor: "#69C779",
        },
      ]}
    />
  ),
  error: (props: BaseToastProps) => (
    <BaseToast
      {...props}
      {...toastProps}
      style={[
        toastProps.style,
        {
          borderLeftColor: "#FE6301",
        },
      ]}
    />
  ),
  warning: (props) => (
    <BaseToast
      {...props}
      {...toastProps}
      style={[
        toastProps.style,
        {
          borderLeftColor: "#FFC107",
        },
      ]}
    />
  ),
};