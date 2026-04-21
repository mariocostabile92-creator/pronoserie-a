/**
 * TeamBadge - Componente per mostrare il logo di una squadra.
 * Usa la stessa URL della webapp: https://media.api-sports.io/football/teams/{id}.png
 * Se la squadra non è nei TEAM_IDS, non renderizza nulla.
 */
import React from 'react';
import { Image } from 'react-native';
import { getTeamBadgeUrl } from '../constants/teamIds';

interface TeamBadgeProps {
  name: string;
  size?: number;
}

export function TeamBadge({ name, size = 20 }: TeamBadgeProps) {
  const url = getTeamBadgeUrl(name);
  if (!url) return null;
  return (
    <Image
      source={{ uri: url }}
      style={{ width: size, height: size, resizeMode: 'contain' }}
    />
  );
}
