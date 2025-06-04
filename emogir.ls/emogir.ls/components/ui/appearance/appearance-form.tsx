import { Select } from "./select";
import { ColorPicker } from "./color-picker";
import { IconPhoto, IconTrash, IconUpload } from "@tabler/icons-react";

export interface AudioTrack {
  id: string;
  url: string;
  title: string;
  icon: string | null;
  order: number;
}

export interface AppearanceState {
  selectedLayout: "modern" | "console" | "femboy" | "discord";
  embedColor: string;
  profile: {
    displayName: string;
    bio: string;
    avatar: string | null;
    banner: string | null;
    decoration: string | null;
  };
  layout: {
    style: string;
  };
  container: {
    backgroundUrl: string | null;
    backdropBlur: string;
    borderWidth: string;
    borderRadius: string;
    glowIntensity: string;
    glassEffect: boolean;
    backgroundColor: string;
    borderColor: string;
    glowColor: string;
  };
  avatar: {
    size: string;
    showBorder: boolean;
    borderWidth: string;
    borderRadius: string;
    glowIntensity: string;
    borderColor: string;
    glowColor: string;
    alignment: string;
  };
  text: {
    titleColor: string;
    titleSize: string;
    titleWeight: string;
    usernameColor: string;
    usernameSize: string;
    bioColor: string;
    bioSize: string;
    bioTextEffectEnabled: boolean;
    bioTextEffect: string;
    bioTextEffectSpeed: number;
  };
  links: {
    backgroundColor: string;
    borderColor: string;
    hoverColor: string;
    gap: string;
    hoverTextColor: string;
    textSize: string;
    iconSize: string;
    iconBgColor: string;
    iconBorderRadius: string;
    primaryTextColor: string;
    secondaryTextColor: string;
    iconColor: string;
    iconBgEnabled: boolean;
    compactMode: boolean;
    disableBackground: boolean;
    disableHover: boolean;
    disableBorder: boolean;
  };
  discord: {
    activityTextColor: string;
    activityBgColor: string;
    activityBorderStyle: string;
    activityLayout: string;
    animationsEnabled: boolean;
    statusIndicatorSize: string;
    presenceAvatarSize: string;
    presenceSecondaryColor: string;
    presenceBgColor: string;
    presenceBorderColor: string;
    presenceTextColor: string;
    guildAvatarSize: string;
    guildBgColor: string;
    guildBorderColor: string;
    guildTitleColor: string;
    guildButtonBgColor: string;
    guildButtonHoverColor: string;
    serverInvite: string;
    statusIndicatorEnabled: boolean;
    activityDisplayType: string;
    activityCompactMode: boolean;
  };
  effects: {
    clickEnabled: boolean;
    clickText: string;
    clickColor: string;
    gradientEnabled: boolean;
    gradientColors: string[];
    gradientType: string;
    gradientDirection: string;
    tiltDisabled: boolean;
  };
  stats: {
    enabled: boolean;
    color: string;
    bgColor: string;
  };
  typography: {
    font: string;
    size: string;
    weight: string;
  };
  terminal: {
    fontFamily: string;
    cursorStyle: string;
    cursorColor: string;
    cursorBlinkSpeed: string;
    typingSpeed: number;
    promptSymbol: string;
    headerControls: boolean;
    statusBarEnabled: boolean;
    lineNumbersEnabled: boolean;
  };
  theme: {
    accentColor: string;
    primaryColor: string;
    secondaryColor: string;
    backgroundColor: string;
    borderColor: string;
    textColor: string;
    glowColor: string;
  };
  audio: {
    tracks: AudioTrack[];
    playerEnabled: boolean;
  };
  lastfm: {
    enabled: boolean;
    compactMode: boolean;
    showScrobbles: boolean;
    showTabs: boolean;
    maxTracks: number;
    themeColor: string;
    bgColor: string;
    textColor: string;
    secondaryColor: string;
  };
}

export interface TerminalSettings {
  fontFamily: string;
  cursorStyle: string;
  cursorColor: string;
  cursorBlinkSpeed: string;
  typingSpeed: number;
  promptSymbol: string;
  headerControls: boolean;
  statusBarEnabled: boolean;
  lineNumbersEnabled: boolean;
}

export interface FemboyThemeSettings {
  accentColor: string;
  primaryColor: string;
  secondaryColor: string;
  backgroundColor: string;
}

export type NestedKeyOf<T> = {
  [K in keyof T & (string | number)]: T[K] extends object
    ? `${K}.${NestedKeyOf<T[K]>}`
    : K;
}[keyof T & (string | number)];

interface AppearanceFormProps {
  state: AppearanceState;
  onChange: (key: NestedKeyOf<AppearanceState>, value: any) => void;
}

export function AppearanceForm({ state, onChange }: AppearanceFormProps) {
  return (
    <div className="space-y-6 p-1">
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-white/80">Profile</h3>
        <div className="flex gap-4">
          <div className="relative group">
            <div className="w-16 h-16 rounded-full bg-primary/5 border border-dashed border-primary/20 flex items-center justify-center">
              {state.profile.avatar ? (
                <img
                  src={state.profile.avatar}
                  alt="Avatar"
                  className="w-full h-full rounded-full object-cover"
                />
              ) : (
                <IconPhoto size={20} className="text-primary/40" />
              )}
              <input type="file" className="hidden" accept="image/*" />
              <div className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 flex items-center justify-center">
                <IconUpload size={14} className="text-white" />
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-3">
            <input
              type="text"
              placeholder="Display Name"
              className="w-full bg-black/20 border border-primary/10 rounded px-3 py-1.5 text-sm"
              value={state.profile.displayName}
              onChange={(e) => onChange("profile.displayName", e.target.value)}
            />
            <input
              type="text"
              placeholder="Bio"
              className="w-full bg-black/20 border border-primary/10 rounded px-3 py-1.5 text-sm"
              value={state.profile.bio}
              onChange={(e) => onChange("profile.bio", e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-medium text-white/80">Theme</h3>
        <div className="grid grid-cols-2 gap-3">
          <ColorPicker
            label="Brand"
            value={state.theme.accentColor}
            onChange={(color) => onChange("theme.accentColor", color)}
          />
          <ColorPicker
            label="Background"
            value={state.theme.backgroundColor}
            onChange={(color) => onChange("theme.backgroundColor", color)}
          />
          <ColorPicker
            label="Text"
            value={state.theme.textColor}
            onChange={(color) => onChange("theme.textColor", color)}
          />
          <ColorPicker
            label="Border"
            value={state.theme.borderColor}
            onChange={(color) => onChange("theme.borderColor", color)}
          />
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-medium text-white/80">Container</h3>
        <div className="grid grid-cols-2 gap-3">
          <ColorPicker
            label="Glow Color"
            value={state.theme.glowColor}
            onChange={(color) => onChange("theme.glowColor", color)}
          />
          <Select
            label="Glow Intensity"
            value={state.container.glowIntensity}
            onChange={(value) => onChange("container.glowIntensity", value)}
            options={[
              { label: "None", value: "0" },
              { label: "Low", value: "0.3" },
              { label: "Medium", value: "0.6" },
              { label: "High", value: "0.9" },
            ]}
          />
          <Select
            label="Backdrop Blur"
            value={state.container.backdropBlur}
            onChange={(value) => onChange("container.backdropBlur", value)}
            options={[
              { label: "None", value: "0" },
              { label: "Light", value: "4px" },
              { label: "Medium", value: "8px" },
              { label: "Heavy", value: "12px" },
            ]}
          />
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-medium text-white/80">Typography</h3>
        <div className="grid grid-cols-2 gap-3">
          <Select
            label="Font"
            value={state.typography.font}
            onChange={(value) => onChange("typography.font", value)}
            options={[
              { label: "Default", value: "default" },
              { label: "Modern", value: "modern" },
              { label: "Classic", value: "classic" },
            ]}
          />
          <Select
            label="Size"
            value={state.typography.size}
            onChange={(value) => onChange("typography.size", value)}
            options={[
              { label: "Small", value: "sm" },
              { label: "Medium", value: "md" },
              { label: "Large", value: "lg" },
            ]}
          />
          <Select
            label="Weight"
            value={state.typography.weight}
            onChange={(value) => onChange("typography.weight", value)}
            options={[
              { label: "Normal", value: "normal" },
              { label: "Medium", value: "medium" },
              { label: "Bold", value: "bold" },
            ]}
          />
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-medium text-white/80">Layout</h3>
        <div className="grid grid-cols-2 gap-3">
          <Select
            label="Style"
            value={state.layout.style}
            onChange={(value) => onChange("layout.style", value)}
            options={[
              { label: "Modern", value: "modern" },
              { label: "Minimal", value: "minimal" },
              { label: "Classic", value: "classic" },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
