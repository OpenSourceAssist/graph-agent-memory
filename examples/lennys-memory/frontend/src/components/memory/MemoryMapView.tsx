"use client";

import { useEffect, useState, useMemo } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Spinner,
  Badge,
  IconButton,
  Link,
} from "@chakra-ui/react";
import { HiX, HiRefresh } from "react-icons/hi";
import { LuExternalLink } from "react-icons/lu";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import type { LocationEntity } from "@/lib/types";

// Dynamically import map components to avoid SSR issues with Leaflet
const MapContainer = dynamic(
  () => import("react-leaflet").then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import("react-leaflet").then((mod) => mod.TileLayer),
  { ssr: false }
);
const Marker = dynamic(
  () => import("react-leaflet").then((mod) => mod.Marker),
  { ssr: false }
);
const Popup = dynamic(
  () => import("react-leaflet").then((mod) => mod.Popup),
  { ssr: false }
);

interface MemoryMapViewProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function MemoryMapView({ isOpen, onClose }: MemoryMapViewProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [locations, setLocations] = useState<LocationEntity[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);

  const loadLocations = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.locations.list(true, 500);
      setLocations(data);

      if (data.length === 0) {
        setError(
          "No geocoded locations available. Run 'make geocode' to add coordinates to Location entities."
        );
      }
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to load locations";
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  // Calculate map bounds from locations
  const mapBounds = useMemo(() => {
    if (locations.length === 0) {
      // Default to world view
      return {
        center: [20, 0] as [number, number],
        zoom: 2,
      };
    }

    if (locations.length === 1) {
      return {
        center: [locations[0].latitude, locations[0].longitude] as [number, number],
        zoom: 10,
      };
    }

    // Calculate center from all locations
    const lats = locations.map((l) => l.latitude);
    const lngs = locations.map((l) => l.longitude);
    const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2;
    const centerLng = (Math.min(...lngs) + Math.max(...lngs)) / 2;

    // Estimate zoom based on spread
    const latSpread = Math.max(...lats) - Math.min(...lats);
    const lngSpread = Math.max(...lngs) - Math.min(...lngs);
    const maxSpread = Math.max(latSpread, lngSpread);

    let zoom = 2;
    if (maxSpread < 1) zoom = 10;
    else if (maxSpread < 5) zoom = 6;
    else if (maxSpread < 20) zoom = 4;
    else if (maxSpread < 60) zoom = 3;

    return {
      center: [centerLat, centerLng] as [number, number],
      zoom,
    };
  }, [locations]);

  // Group locations by subtype for stats
  const locationStats = useMemo(() => {
    const stats: Record<string, number> = {};
    for (const loc of locations) {
      const subtype = loc.subtype || "Unknown";
      stats[subtype] = (stats[subtype] || 0) + 1;
    }
    return stats;
  }, [locations]);

  useEffect(() => {
    if (isOpen) {
      loadLocations();
      // Small delay to ensure CSS is loaded
      setTimeout(() => setMapReady(true), 100);
    } else {
      setMapReady(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <Box
        position="fixed"
        top={0}
        left={0}
        right={0}
        bottom={0}
        bg="blackAlpha.600"
        zIndex={1000}
        onClick={onClose}
      />

      {/* Map View Modal */}
      <Box
        position="fixed"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        width={{ base: "95%", md: "90%", lg: "85%" }}
        height={{ base: "90%", md: "85%" }}
        bg="white"
        borderRadius="xl"
        boxShadow="2xl"
        zIndex={1001}
        display="flex"
        flexDirection="column"
        overflow="hidden"
      >
        {/* Header */}
        <VStack gap={0} borderBottom="1px solid" borderColor="gray.200">
          <HStack
            justifyContent="space-between"
            p={4}
            width="100%"
            bg="gray.50"
          >
            <VStack align="start" gap={0}>
              <Text fontSize="xl" fontWeight="bold">
                Location Map
              </Text>
              <Text fontSize="xs" color="gray.600">
                Locations mentioned in podcast transcripts
              </Text>
              {locations.length > 0 && (
                <HStack gap={2} mt={1}>
                  <Badge colorPalette="blue" fontSize="xs">
                    {locations.length} locations
                  </Badge>
                  {Object.entries(locationStats)
                    .slice(0, 3)
                    .map(([subtype, count]) => (
                      <Badge key={subtype} colorPalette="gray" fontSize="xs">
                        {count} {subtype.toLowerCase()}
                      </Badge>
                    ))}
                </HStack>
              )}
            </VStack>

            <HStack gap={2}>
              <IconButton
                aria-label="Refresh locations"
                size="sm"
                onClick={loadLocations}
                disabled={isLoading}
              >
                <HiRefresh />
              </IconButton>
              <IconButton
                aria-label="Close map view"
                size="sm"
                variant="ghost"
                onClick={onClose}
              >
                <HiX />
              </IconButton>
            </HStack>
          </HStack>
        </VStack>

        {/* Map Container */}
        <Box flex={1} position="relative" bg="gray.100">
          {isLoading ? (
            <VStack height="100%" justifyContent="center" gap={4}>
              <Spinner size="xl" />
              <Text color="gray.600">Loading locations...</Text>
            </VStack>
          ) : error ? (
            <VStack height="100%" justifyContent="center" gap={4} p={6}>
              <Text fontSize="lg" color="red.500" textAlign="center">
                {error}
              </Text>
              <Button colorPalette="blue" onClick={loadLocations}>
                Try Again
              </Button>
            </VStack>
          ) : mapReady && locations.length > 0 ? (
            <Box height="100%" width="100%">
              <MapContainer
                center={mapBounds.center}
                zoom={mapBounds.zoom}
                style={{ height: "100%", width: "100%" }}
                scrollWheelZoom={true}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {locations.map((location) => (
                  <Marker
                    key={location.id}
                    position={[location.latitude, location.longitude]}
                  >
                    <Popup>
                      <Box maxW="300px">
                        <Text fontWeight="bold" fontSize="md" mb={1}>
                          {location.name}
                        </Text>
                        {location.subtype && (
                          <Badge colorPalette="purple" size="sm" mb={2}>
                            {location.subtype}
                          </Badge>
                        )}
                        {(location.enriched_description || location.description) && (
                          <Text fontSize="sm" color="gray.600" mb={2}>
                            {(location.enriched_description || location.description)?.slice(0, 200)}
                            {((location.enriched_description || location.description)?.length || 0) > 200 && "..."}
                          </Text>
                        )}
                        {location.wikipedia_url && (
                          <Link
                            href={location.wikipedia_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            fontSize="sm"
                            color="blue.500"
                            display="flex"
                            alignItems="center"
                            gap={1}
                            mb={2}
                          >
                            Wikipedia <LuExternalLink size={12} />
                          </Link>
                        )}
                        {location.conversations.length > 0 && (
                          <Box mt={2} pt={2} borderTop="1px solid" borderColor="gray.200">
                            <Text fontSize="xs" fontWeight="semibold" color="gray.500" mb={1}>
                              Mentioned in {location.conversations.length} episode(s):
                            </Text>
                            <VStack align="start" gap={0.5}>
                              {location.conversations.slice(0, 3).map((conv) => (
                                <Text key={conv.id} fontSize="xs" color="gray.600">
                                  {conv.title || conv.id}
                                </Text>
                              ))}
                              {location.conversations.length > 3 && (
                                <Text fontSize="xs" color="gray.400">
                                  +{location.conversations.length - 3} more
                                </Text>
                              )}
                            </VStack>
                          </Box>
                        )}
                        <Text fontSize="xs" color="gray.400" mt={2}>
                          {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
                        </Text>
                      </Box>
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </Box>
          ) : null}
        </Box>

        {/* Footer */}
        {locations.length > 0 && !isLoading && !error && (
          <HStack
            p={3}
            borderTop="1px solid"
            borderColor="gray.200"
            justifyContent="center"
            gap={4}
            flexWrap="wrap"
            bg="gray.50"
          >
            <Text fontSize="xs" color="gray.600">
              Click markers to view location details | Scroll to zoom | Drag to pan
            </Text>
          </HStack>
        )}
      </Box>
    </>
  );
}
