'use client';
import React, { useState, useEffect } from 'react';
import { Power, Loader, UserCircle, Clock, Wifi, WifiOff } from 'lucide-react';
import L from 'leaflet'; // Leaflet for maps
import 'leaflet/dist/leaflet.css'; // Leaflet CSS

// System status types
type SystemStatus = 'disconnected' | 'connecting' | 'starting' | 'running' | 'paused' | 'stopped' | 'error';



// Blue pin icon
const BluePinIcon = L.icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
  iconSize: [25, 41], // Size of the icon
  iconAnchor: [12, 41], // Point of the icon which will correspond to marker's location
  shadowSize: [41, 41], // Size of the shadow
  shadowAnchor: [12, 41], // Point of the shadow which will correspond to marker's location
  popupAnchor: [1, -34], // Point from which the popup should open relative to the iconAnchor
});

function App() {
  const [driverName, setDriverName] = useState('');
  const [systemStarted, setSystemStarted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [systemStatus, setSystemStatus] = useState<SystemStatus>('disconnected');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [map, setMap] = useState<L.Map | null>(null); // Leaflet map instance
  const [marker, setMarker] = useState<L.Marker | null>(null); // Marker for user location

  // Update current time every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Initialize map
  useEffect(() => {
    if (systemStarted) {
      const leafletMap = L.map('map').setView([51.505, -0.09], 13); // Default center
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
      }).addTo(leafletMap);
      setMap(leafletMap);

      // Add a marker for the user's location with a blue pin
      const marker = L.marker([51.505, -0.09], { icon: BluePinIcon }).addTo(leafletMap);
      setMarker(marker);

      return () => {
        leafletMap.remove();
      };
    }
  }, [systemStarted]);

  // Track user's real-time location
  useEffect(() => {
    if (systemStarted && map && marker) {
      const watchId = navigator.geolocation.watchPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          map.setView([latitude, longitude], 13); // Update map center
          marker.setLatLng([latitude, longitude]); // Update marker position
        },
        (error) => {
          console.error('Error getting location:', error);
          setError('Unable to retrieve your location.');
        },
        { enableHighAccuracy: true }
      );

      return () => navigator.geolocation.clearWatch(watchId);
    }
  }, [systemStarted, map, marker]);

  // Check backend health on page load
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const response = await fetch('http://localhost:5000/health');
        if (!response.ok) {
          throw new Error('Backend server is not running.');
        }
        setSystemStatus('stopped'); // Backend is running
      } catch (error) {
        console.error('Backend health check failed:', error);
        setError('Backend server is not running. Please ensure the server is started.');
        setSystemStatus('disconnected');
      }
    };

    checkBackendHealth();
  }, []);

  // Clear session storage on page reload
  useEffect(() => {
    const handleBeforeUnload = () => {
      sessionStorage.removeItem('messages'); // Clear messages
      sessionStorage.setItem('status', 'disconnected'); // Set status to disconnected
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  const handleStartSystem = async () => {
    if (!driverName) {
      setError('Please enter your name.');
      return;
    }

    setLoading(true);
    setError('');
    setSystemStatus('starting');

    try {
      const response = await fetch('http://localhost:5000/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ driver_name: driverName }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to start the system.');
      }

      const data = await response.json();
      if (data.success) {
        setSystemStarted(true);
        setSystemStatus('running');
      } else {
        throw new Error(data.message || 'Failed to start the system.');
      }
    } catch (error) {
      console.error('Error starting system:', error);
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError('An unknown error occurred.');
      }
      setSystemStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleStopSystem = async () => {
    try {
      const response = await fetch('http://localhost:5000/stop', {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to stop the system.');
      }

      setSystemStarted(false);
      setSystemStatus('stopped');
    } catch (error) {
      console.error('Error stopping system:', error);
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError('Failed to stop the system. Please try again.');
      }
    }
  };

  const getStatusColor = (status: SystemStatus) => {
    switch (status) {
      case 'running': return 'text-green-600';
      case 'paused': return 'text-yellow-600';
      case 'stopped': return 'text-red-600';
      case 'starting': return 'text-blue-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: SystemStatus) => {
    switch (status) {
      case 'running': return <Wifi className="w-4 h-4 text-green-500" />;
      case 'disconnected': return <WifiOff className="w-4 h-4 text-red-500" />;
      default: return <Wifi className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
      <div className="bg-white p-8 border border-blue-300 rounded-lg shadow-lg w-full max-w-4xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <UserCircle className="w-10 h-10 text-gray-700" />
            <div>
              <h1 className="text-xl font-bold text-blue-600">{driverName || 'Driver'}</h1>
              <div className="flex items-center space-x-1">
                {getStatusIcon(systemStatus)}
                <span className={`text-sm ${getStatusColor(systemStatus)}`}>
                  {systemStatus === 'disconnected' ? 'Offline' : 'Online'}
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-gray-700">
            <Clock className="w-5 h-5 text-blue-600" />
            <span className="text-sm ">
              {currentTime.toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* System Status */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-center text-gray-800 mb-2">
            <span className='text-4xl text-blue-600'>Robin</span> - Powered for the Open Road
          </h2>
          <div className={`text-center font-semibold capitalize ${getStatusColor(systemStatus)}`}>
            System Status: {systemStatus}
            {systemStatus === 'starting' && <Loader className="inline-block w-4 h-4 ml-2 animate-spin" />}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-md">
            {error}
          </div>
        )}

        {/* Start/Stop System */}
        {!systemStarted ? (
          <div>
            <div className="mb-4">
              <label htmlFor="driver-name" className="block text-sm font-medium text-gray-700">
                Driver Name
              </label>
              <input
                id="driver-name"
                type="text"
                placeholder="Enter your name"
                value={driverName}
                onChange={(e) => setDriverName(e.target.value)}
                className="mt-1 block w-full text-black px-4 py-2 border border-blue-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <button
              onClick={handleStartSystem}
              disabled={loading || systemStatus === 'disconnected'}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading ? (
                <>
                  <Loader className="w-5 h-5 mr-2 animate-spin" />
                  Starting System...
                </>
              ) : (
                <>
                  <Power className="w-5 h-5 mr-2" />
                  Start System
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="flex justify-center">
            <button
              onClick={handleStopSystem}
              className="w-full bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 flex items-center justify-center"
            >
              <Power className="w-5 h-5 mr-2" />
              Stop System
            </button>
          </div>
        )}

        {/* Real-Time Map */}
        {systemStarted && (
          <div className="mt-6">
            <h3 className="text-xl font-bold text-gray-800 mb-4">My Location</h3>
            <div id="map" className="h-96 rounded-lg shadow-md"></div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;