import { CheckCircle, FileText, RotateCcw } from 'lucide-react';
import type { SubmitResponse } from '../types';

interface ConfirmationProps {
  result: SubmitResponse;
  onReset: () => void;
}

export default function Confirmation({ result, onReset }: ConfirmationProps) {
  return (
    <div className="flex flex-col items-center gap-6 text-center w-full max-w-lg">
      <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center">
        <CheckCircle className="w-10 h-10 text-green-600" />
      </div>

      <div>
        <h2 className="text-2xl font-bold mb-2">Complaint Submitted!</h2>
        <p className="text-gray-600">
          Your service request has been filed (mock submission).
        </p>
      </div>

      <div className="card bg-green-50 w-full">
        <div className="flex items-center gap-3 mb-4">
          <FileText className="w-6 h-6 text-green-600" />
          <h3 className="font-bold text-lg">Service Request #{result.sr_number}</h3>
        </div>

        <div className="space-y-3 text-left">
          <div className="flex justify-between">
            <span className="text-gray-500">Status</span>
            <span className="font-medium text-green-700">Mock Submitted</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Service</span>
            <span className="font-medium">{result.payload.ka}</span>
          </div>
          {result.payload.description && (
            <div className="border-t pt-3">
              <span className="text-gray-500 block text-sm mb-1">Description</span>
              <p className="text-sm text-gray-700">{result.payload.description}</p>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-gray-500">Address</span>
            <span className="font-medium">{result.payload.address}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Borough</span>
            <span className="font-medium">{result.payload.borough}</span>
          </div>
          {result.payload.photo_b64 && (
            <div className="flex justify-between">
              <span className="text-gray-500">Photo</span>
              <span className="font-medium text-green-600">Attached</span>
            </div>
          )}
        </div>
      </div>

      <p className="text-sm text-gray-500 max-w-sm">
        In a real scenario, this would be submitted to NYC 311. For this demo,
        we've generated a mock confirmation number.
      </p>

      <button onClick={onReset} className="btn-primary flex items-center gap-2">
        <RotateCcw className="w-4 h-4" />
        File Another Complaint
      </button>
    </div>
  );
}
