interface ValidationError {
  code: string;
  message: string;
  field: string;
  value?: any;
}

const ERROR_CODES = {
  INVALID_HEX_COLOR: "30001",
  INVALID_CSS_UNIT: "30002",
  INVALID_GLOW_INTENSITY: "30003",
  REQUIRED_FIELD: "30004",
  INVALID_USERNAME: "40001",
  USERNAME_TAKEN: "40002",
  INVALID_DISPLAY_NAME: "40003",
  INVALID_PAGE_TITLE: "40004",
  INVALID_SEO_DESCRIPTION: "40005",
  INVALID_LAYOUT_STYLE: "60001",
  INVALID_BACKDROP_BLUR: "60002",
  INVALID_BORDER_WIDTH: "60003",
  INVALID_BORDER_RADIUS: "60004",
  INVALID_FONT_SIZE: "60005",
  INVALID_FONT_WEIGHT: "60006",
  INVALID_GAP: "60007",
  INVALID_PADDING: "60008",
  INVALID_ICON_SIZE: "60009",
  INVALID_TEXT_SIZE: "60010",
  INVALID_AVATAR_SIZE: "60011",
  SERVER_ERROR: "50001",
} as const;

const isValidHexColor = (value: string): boolean => {
  return /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(value);
};

const isValidCSSUnit = (value: string): boolean => {
  return /^-?\d*\.?\d+(px|rem|em|%|vh|vw)?$/.test(value);
};

export interface IconSettings {
  backgroundColor: string;
  size: string;
  borderRadius: string;
  borderColor: string;
  glowColor: string;
  glowIntensity: string;
}

export const validateIconSettings = (
  settings: Partial<IconSettings>,
): ValidationError[] => {
  const errors: ValidationError[] = [];

  if (!isValidHexColor(settings.backgroundColor || "")) {
    errors.push({
      code: ERROR_CODES.INVALID_HEX_COLOR,
      message: "Invalid background color format (e.g., #FF0000)",
      field: "backgroundColor",
      value: settings.backgroundColor,
    });
  }

  if (!isValidCSSUnit(settings.size || "")) {
    errors.push({
      code: ERROR_CODES.INVALID_CSS_UNIT,
      message: "Invalid size format (e.g., 24px, 1.5rem)",
      field: "size",
      value: settings.size,
    });
  }

  if (!isValidCSSUnit(settings.borderRadius || "")) {
    errors.push({
      code: ERROR_CODES.INVALID_CSS_UNIT,
      message: "Invalid border radius format",
      field: "borderRadius",
      value: settings.borderRadius,
    });
  }

  if (!isValidHexColor(settings.borderColor || "")) {
    errors.push({
      code: ERROR_CODES.INVALID_HEX_COLOR,
      message: "Invalid border color format",
      field: "borderColor",
      value: settings.borderColor,
    });
  }

  if (!isValidHexColor(settings.glowColor || "")) {
    errors.push({
      code: ERROR_CODES.INVALID_HEX_COLOR,
      message: "Invalid glow color format",
      field: "glowColor",
      value: settings.glowColor,
    });
  }

  if (!settings.glowIntensity?.match(/^0(\.\d+)?$|^1(\.0+)?$/)) {
    errors.push({
      code: ERROR_CODES.INVALID_GLOW_INTENSITY,
      message: "Glow intensity must be between 0 and 1",
      field: "glowIntensity",
      value: settings.glowIntensity,
    });
  }

  return errors;
};

export interface AppearanceValidation {
  layoutStyle?: string;
  container: {
    backgroundColor?: string;
    backdropBlur?: string;
    borderColor?: string;
    borderWidth?: string;
    borderRadius?: string;
    glowColor?: string;
    glowIntensity?: string;
  };
  avatar: {
    size?: string;
    borderWidth?: string;
    borderColor?: string;
    borderRadius?: string;
    glowColor?: string;
    glowIntensity?: string;
  };
  text: {
    titleColor?: string;
    titleSize?: string;
    titleWeight?: string;
    usernameColor?: string;
    usernameSize?: string;
    bioColor?: string;
    bioSize?: string;
  };
  links: {
    backgroundColor?: string;
    hoverColor?: string;
    borderColor?: string;
    gap?: string;
    primaryTextColor?: string;
    secondaryTextColor?: string;
    hoverTextColor?: string;
    textSize?: string;
    iconSize?: string;
    iconColor?: string;
    iconBgColor?: string;
    iconBorderRadius?: string;
  };
  discord: {
    presenceBgColor?: string;
    presenceBorderColor?: string;
    presenceAvatarSize?: string;
    presenceTextColor?: string;
    presenceSecondaryColor?: string;
    guildBgColor?: string;
    guildBorderColor?: string;
    guildAvatarSize?: string;
    guildTitleColor?: string;
    guildButtonBgColor?: string;
    guildButtonHoverColor?: string;
  };
  effects: {
    clickEnabled?: boolean;
    clickText?: string;
    clickColor?: string;
    gradientEnabled?: boolean;
    gradientColors?: string[];
    gradientType?: string;
    gradientDirection?: string;
  };
  stats: {
    enabled?: boolean;
    color?: string;
    backgroundColor?: string;
  };
  typography: {
    font?: string;
    size?: string;
    weight?: string;
  };
  terminal: {
    fontFamily?: string;
    cursorStyle?: string;
    cursorColor?: string;
    cursorBlinkSpeed?: string;
    typingSpeed?: number;
    promptSymbol?: string;
    headerControls?: boolean;
    statusBarEnabled?: boolean;
    lineNumbersEnabled?: boolean;
  };
}

const VALID_LAYOUT_STYLES = ["modern", "console", "femboy", "discord"];

export const validateAppearance = (
  data: AppearanceValidation,
): ValidationError[] => {
  const errors: ValidationError[] = [];

  if (data.layoutStyle && !VALID_LAYOUT_STYLES.includes(data.layoutStyle)) {
    errors.push({
      code: ERROR_CODES.INVALID_LAYOUT_STYLE,
      message: "Invalid layout style",
      field: "layoutStyle",
      value: data.layoutStyle,
    });
  }

  if (data.container) {
    if (
      data.container.backgroundColor &&
      !isValidHexColor(data.container.backgroundColor)
    ) {
      errors.push({
        code: ERROR_CODES.INVALID_HEX_COLOR,
        message: "Invalid background color format",
        field: "container.backgroundColor",
        value: data.container.backgroundColor,
      });
    }

    if (
      data.container.backdropBlur &&
      !isValidCSSUnit(data.container.backdropBlur)
    ) {
      errors.push({
        code: ERROR_CODES.INVALID_CSS_UNIT,
        message: "Invalid backdrop blur format",
        field: "container.backdropBlur",
        value: data.container.backdropBlur,
      });
    }

    if (
      data.container.glowIntensity &&
      !data.container.glowIntensity.match(/^0(\.\d+)?$|^1(\.0+)?$/)
    ) {
      errors.push({
        code: ERROR_CODES.INVALID_GLOW_INTENSITY,
        message: "Glow intensity must be between 0 and 1",
        field: "container.glowIntensity",
        value: data.container.glowIntensity,
      });
    }
  }

  if (data.text) {
    if (data.text.titleColor && !isValidHexColor(data.text.titleColor)) {
      errors.push({
        code: ERROR_CODES.INVALID_HEX_COLOR,
        message: "Invalid title color format",
        field: "text.titleColor",
        value: data.text.titleColor,
      });
    }
  }

  return errors;
};

export interface SettingsValidation {
  displayName?: string;
  username?: string;
  seoDescription?: string;
  pageTitle?: string;
}

export const validateSettingsData = (
  settings: SettingsValidation,
  currentUsername?: string,
): ValidationError[] => {
  const errors: ValidationError[] = [];

  if (settings.displayName && settings.displayName.length > 50) {
    errors.push({
      code: "20001",
      message: "Display name cannot exceed 50 characters",
      field: "displayName",
      value: settings.displayName,
    });
  }

  if (!settings.username) {
    errors.push({
      code: "20002",
      message: "Username is required",
      field: "username",
    });
  } else if (
    (!currentUsername || settings.username !== currentUsername) &&
    !/^[a-zA-Z0-9_-]{3,20}$/.test(settings.username)
  ) {
    errors.push({
      code: "20003",
      message:
        "Username must be 3-20 characters and can only contain letters, numbers, underscores, and hyphens",
      field: "username",
      value: settings.username,
    });
  }

  if (settings.pageTitle && settings.pageTitle.length > 60) {
    errors.push({
      code: "20004",
      message: "Page title cannot exceed 60 characters",
      field: "pageTitle",
      value: settings.pageTitle,
    });
  }

  if (settings.seoDescription && settings.seoDescription.length > 160) {
    errors.push({
      code: "20005",
      message: "SEO description cannot exceed 160 characters",
      field: "seoDescription",
      value: settings.seoDescription,
    });
  }

  return errors;
};

export const PASSWORD_MIN_LENGTH = 8;

export const validatePassword = (password: string) => {
  const errors: string[] = [];

  if (password.length < PASSWORD_MIN_LENGTH) {
    errors.push(
      `Password must be at least ${PASSWORD_MIN_LENGTH} characters long`,
    );
  }

  if (!/[A-Z]/.test(password)) {
    errors.push("Password must contain at least one uppercase letter");
  }

  if (!/[a-z]/.test(password)) {
    errors.push("Password must contain at least one lowercase letter");
  }

  if (!/[0-9]/.test(password)) {
    errors.push("Password must contain at least one number");
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};
