import { useState, useEffect } from 'react';
import { MapPin, Camera, Loader2, Send, Mic, Square } from 'lucide-react';
import type { SubmitPayload } from '../types';
import { BOROUGHS } from '../types';
import FieldMic from './FieldMic';

interface ServiceFormProps {
  pickedKa: string;
  kaTitle: string;
  formData: {
    description: string;
    address: string;
    borough: string;
    apartment: string;
    locationDetails: string;
  };
  onSubmit: (payload: SubmitPayload) => void;
  onBack: () => void;
  isSubmitting: boolean;
  onFieldTranscript?: (field: string, transcript: string) => void;
  onGeneralTranscript?: (transcript: string) => void;
}

export default function ServiceForm({
  pickedKa,
  kaTitle,
  formData,
  onSubmit,
  onBack,
  isSubmitting,
  onFieldTranscript,
  onGeneralTranscript,
}: ServiceFormProps) {
  const [description, setDescription] = useState(formData.description || '');
  const [address, setAddress] = useState(formData.address || '');
  const [borough, setBorough] = useState(formData.borough || '');
  const [apartment, setApartment] = useState(formData.apartment || '');
  const [locationDetails, setLocationDetails] = useState(formData.locationDetails || '');
  const [photo, setPhoto] = useState<string | null>(null);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState('');
  const [generalMicRecording, setGeneralMicRecording] = useState(false);

  // Sync with external formData changes (e.g., from agent updates)
  useEffect(() => {
    setDescription(formData.description || '');
    setAddress(formData.address || '');
    setBorough(formData.borough || '');
    setApartment(formData.apartment || '');
    setLocationDetails(formData.locationDetails || '');
  }, [formData]);

  // Auto-fill from GPS
  const fillFromGPS = () => {
    setGpsLoading(true);
    setGpsError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&addressdetails=1`,
            { headers: { 'User-Agent': '311-voice/0.1' } }
          );
          const data = await res.json();
          const addr = data.address;
          const street = addr.house_number
            ? `${addr.house_number} ${addr.road || ''}`
            : addr.road || '';
          setAddress(street);
          
          // Try to extract borough from multiple Nominatim fields
          const boroName = addr.borough || addr.city || addr.county || addr.suburb || '';
          const displayName = data.display_name || '';
          const searchText = `${boroName} ${displayName}`.toLowerCase();
          
          const matched = BOROUGHS.find((b) => {
            const nameLower = b.name.toLowerCase();
            return searchText.includes(nameLower) ||
              (b.name === 'The Bronx' && searchText.includes('bronx')) ||
              (b.name === 'Staten Island' && searchText.includes('staten island'));
          });
          if (matched) setBorough(matched.code);
        } catch (e) {
          setGpsError('Could not reverse geocode');
        } finally {
          setGpsLoading(false);
        }
      },
      (err) => {
        setGpsError(err.message);
        setGpsLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handlePhotoCapture = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      setPhoto(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      ka: pickedKa,
      description,
      address,
      borough,
      apartment: apartment || undefined,
      locationDetails: locationDetails || undefined,
      photo_b64: photo || undefined,
    });
  };

  const handleFieldTranscript = (field: string) => (transcript: string) => {
    if (onFieldTranscript && transcript) {
      onFieldTranscript(field, transcript);
    }
  };

  const handleGeneralMic = () => {
    if (generalMicRecording) {
      setGeneralMicRecording(false);
      return;
    }
    setGeneralMicRecording(true);
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';
      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const text = event.results[0][0].transcript;
        if (onGeneralTranscript && text) {
          onGeneralTranscript(text);
        }
        setGeneralMicRecording(false);
      };
      recognition.onerror = () => {
        setGeneralMicRecording(false);
      };
      recognition.onend = () => {
        setGeneralMicRecording(false);
      };
      recognition.start();
    } else {
      setGeneralMicRecording(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-full max-w-xl">
      <div className="text-center mb-2">
        <h2 className="text-2xl font-bold mb-1">File a 311 Complaint</h2>
        <p className="text-nyc-blue font-medium">{kaTitle}</p>
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        <div className="flex gap-2 items-start">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            rows={3}
            className="input-field flex-1"
            placeholder="Describe the issue in detail..."
          />
          <div className="flex-shrink-0 pt-1">
            <FieldMic
              onTranscript={handleFieldTranscript('description')}
              size="sm"
            />
          </div>
        </div>
      </div>

      {/* Address + GPS */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Address
        </label>
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
            className="input-field flex-1"
            placeholder="123 Main St"
          />
          <FieldMic
            onTranscript={handleFieldTranscript('address')}
            size="sm"
          />
          <button
            type="button"
            onClick={fillFromGPS}
            disabled={gpsLoading}
            className="btn-secondary px-3 py-2 flex items-center gap-1"
            title="Use current location"
          >
            {gpsLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <MapPin className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">GPS</span>
          </button>
        </div>
        {gpsError && <p className="text-red-500 text-xs mt-1">{gpsError}</p>}
      </div>

      {/* Borough */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Borough
        </label>
        <div className="flex gap-2 items-center">
          <select
            value={borough}
            onChange={(e) => setBorough(e.target.value)}
            required
            className="input-field flex-1"
          >
            <option value="">Select borough...</option>
            {BOROUGHS.map((b) => (
              <option key={b.code} value={b.code}>
                {b.name}
              </option>
            ))}
          </select>
          <FieldMic
            onTranscript={handleFieldTranscript('borough')}
            size="sm"
          />
        </div>
      </div>

      {/* Apartment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Apartment / Unit (optional)
        </label>
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={apartment}
            onChange={(e) => setApartment(e.target.value)}
            className="input-field flex-1"
            placeholder="4B"
          />
          <FieldMic
            onTranscript={handleFieldTranscript('apartment')}
            size="sm"
          />
        </div>
      </div>

      {/* Location details */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Location Details (optional)
        </label>
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={locationDetails}
            onChange={(e) => setLocationDetails(e.target.value)}
            className="input-field flex-1"
            placeholder="Near the northeast corner, by the mailbox"
          />
          <FieldMic
            onTranscript={handleFieldTranscript('locationDetails')}
            size="sm"
          />
        </div>
      </div>

      {/* Photo */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Attach Photo (optional)
        </label>
        <div className="flex items-center gap-3">
          <label className="btn-secondary cursor-pointer flex items-center gap-2">
            <Camera className="w-4 h-4" />
            <span>{photo ? 'Change Photo' : 'Add Photo'}</span>
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handlePhotoCapture}
              className="hidden"
            />
          </label>
          {photo && (
            <span className="text-sm text-green-600 font-medium">
              Photo attached
            </span>
          )}
        </div>
        {photo && (
          <img
            src={photo}
            alt="Attached"
            className="mt-2 w-32 h-32 object-cover rounded-lg border"
          />
        )}
      </div>

      {/* General mic at bottom */}
      <div className="flex flex-col items-center gap-2 mt-2">
        <button
          type="button"
          onClick={handleGeneralMic}
          className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${
            generalMicRecording
              ? 'bg-red-500 text-white animate-pulse'
              : 'bg-nyc-orange text-white hover:bg-orange-600'
          }`}
          title={generalMicRecording ? 'Tap to stop recording' : 'Tap to describe changes'}
        >
          {generalMicRecording ? (
            <Square className="w-6 h-6" />
          ) : (
            <Mic className="w-6 h-6" />
          )}
        </button>
        <p className="text-xs text-gray-500">
          {generalMicRecording
            ? 'Recording... describe any changes needed'
            : 'Tap to describe changes'}
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-center mt-4">
        <button type="button" onClick={onBack} className="btn-secondary">
          Back
        </button>
        <button
          type="submit"
          disabled={isSubmitting || !description || !address || !borough}
          className="btn-primary flex items-center gap-2"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Submitting...
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              Submit
            </>
          )}
        </button>
      </div>
    </form>
  );
}

// TypeScript declarations for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
  interface SpeechRecognitionEvent extends Event {
    results: SpeechRecognitionResultList;
  }
}
