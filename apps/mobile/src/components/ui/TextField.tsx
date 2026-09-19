import { ComponentProps, forwardRef, ReactNode, useState } from "react";
import { TextInput, View } from "react-native";

import { AppText } from "./AppText";

import { useTheme } from "@/theme/ThemeProvider";

type TextFieldProps = ComponentProps<typeof TextInput> & {
  label: string;
  error?: string;
  endAdornment?: ReactNode;
};

export const TextField = forwardRef<TextInput, TextFieldProps>(
  function TextField(
    { label, error, endAdornment, style, onBlur, onFocus, ...props },
    ref,
  ) {
    const theme = useTheme();
    const [focused, setFocused] = useState(false);

    return (
      <View style={{ gap: theme.spacing.xs }}>
        <AppText variant="caption" style={{ fontWeight: "600" }}>
          {label}
        </AppText>
        <View style={{ position: "relative" }}>
          <TextInput
            ref={ref}
            accessibilityLabel={label}
            placeholderTextColor={theme.colors.textMuted}
            selectionColor={theme.colors.primary}
            cursorColor={theme.colors.primary}
            onFocus={(event) => {
              setFocused(true);
              onFocus?.(event);
            }}
            onBlur={(event) => {
              setFocused(false);
              onBlur?.(event);
            }}
            style={[
              theme.typography.body,
              {
                minHeight: 54,
                color: theme.colors.text,
                backgroundColor: theme.colors.surfaceMuted,
                borderColor: error
                  ? theme.colors.danger
                  : focused
                    ? theme.colors.primary
                    : "transparent",
                borderRadius: theme.radius.md,
                borderWidth: 1,
                paddingLeft: theme.spacing.md,
                paddingRight: endAdornment ? 56 : theme.spacing.md,
                paddingVertical: theme.spacing.sm,
              },
              style,
            ]}
            {...props}
          />
          {endAdornment ? (
            <View
              style={{
                position: "absolute",
                right: 6,
                top: 5,
                width: 44,
                height: 44,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {endAdornment}
            </View>
          ) : null}
        </View>
        {error ? (
          <AppText variant="caption" color="danger">
            {error}
          </AppText>
        ) : null}
      </View>
    );
  },
);
