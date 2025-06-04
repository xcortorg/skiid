import { UniqueIdentifier } from "@dnd-kit/core";

export interface Link {
  id: string;
  title: string;
  url: string;
  iconUrl?: string;
  clicks: number;
  enabled: boolean;
  position: number;
  iconBackgroundColor?: string;
  iconSize?: string;
  iconBorderRadius?: string;
  iconBorderColor?: string;
  iconGlowColor?: string;
  iconGlowIntensity?: string;
  backgroundColor?: string;
  hoverColor?: string;
  borderColor?: string;
  gap?: string;
  primaryTextColor?: string;
  secondaryTextColor?: string;
  hoverTextColor?: string;
  textSize?: string;
  iconColor?: string;
  iconBgColor?: string;
  preset?: string;
}
