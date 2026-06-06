import { useState, useEffect } from 'react';
import { MapPin, Camera, Loader2, Send } from 'lucide-react';
import type { SubmitPayload, ExtractedFields, Borough } from '../types';
import { BOROUGHS } from '../types';

interface ServiceFormProps {
  pickedKa: string;
  kaTitle: string;
  extractedFields: ExtractedFields;
  onSubmit: (payload: SubmitPayload) => void;
  onBack: () => void;
  isSubmitting: boolean;
}

export default function ServiceForm({
  pickedKa,
  kaTitle,
  extractedFields,
  onSubmit,
  onBack,
  isSubmitting,
}: ServiceFormProps) {
  const [description, setDescription] = useState(extractedFields.description || '');
  const [address, setAddress] = useState(extractedFields.address || '');
  const [borough, setBorough] = useState('');
  const [apartment, setApartment] = useState(extractedFields.apartment || '');
  const [locationDetails, setLocationDetails] = useState(extractedFields.locationDetails || '');
  const [photo, setPhoto] = useState<string | null>(null);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState('');

  // Auto-fill from GPS
  const fillFromGPS = () => {
    setGpsLoading(true);
    setGpsError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        try {
          // Reverse geocode using Nominatim (free, no key)
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
          // Map borough
          const boroName =
            addr.borough || addr.city || addr.county || '';
          const matched = BOROUGHS.find(
            (b) =>
              boroName.toLowerCase().includes(b.name.toLowerCase()) ||
              (b.name === 'The Bronx' && boroName.toLowerCase().includes('bronx'))
          );
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
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
          rows={3}
          className="input-field"
          placeholder="Describe the issue in detail..."
        />
      </div>

      {/* Address + GPS */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Address
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
            className="input-field flex-1"
            placeholder="123 Main St"
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
        <select
          value={borough}
          onChange={(e) => setBorough(e.target.value)}
          required
          className="input-field"
        >
          <option value="">Select borough...</option>
          {BOROUGHS.map((b) => (
            <option key={b.code} value={b.code}>
              {b.name}
            </option>
          ))}
        </select>
      </div>

      {/* Apartment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Apartment / Unit (optional)
        </label>
        <input
          type="text"
          value={apartment}
          onChange={(e) => setApartment(e.target.value)}
          className="input-field"
          placeholder="4B"
        />
      </div>

      {/* Location details */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Location Details (optional)
        </label>
        <input
          type="text"
          value={locationDetails}
          onChange={(e) => setLocationDetails(e.target.value)}
          className="input-field"
          placeholder="Near the northeast corner, by the mailbox"
        />
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
