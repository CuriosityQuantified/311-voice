import type { MatchResponse } from '../types';
import { CheckCircle, ArrowRight, Building2 } from 'lucide-react';

interface MatchResultsProps {
  result: MatchResponse;
  onContinue: () => void;
  onBack: () => void;
}

export default function MatchResults({ result, onContinue, onBack }: MatchResultsProps) {
  const picked = result.candidates.find((c) => c.ka === result.picked_ka);

  return (
    <div className="flex flex-col gap-6 w-full max-w-2xl">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">We found the right service</h2>
        <p className="text-gray-600">Based on your description, here's what we recommend</p>
      </div>

      {/* Picked match */}
      <div className="card bg-blue-50 border-2 border-nyc-blue">
        <div className="flex items-start gap-3">
          <CheckCircle className="w-6 h-6 text-nyc-blue flex-shrink-0 mt-1" />
          <div>
            <h3 className="font-bold text-lg text-nyc-blue">
              {picked?.title || 'Recommended Service'}
            </h3>
            <p className="text-gray-700 mt-1">{picked?.description}</p>
          </div>
        </div>
      </div>

      {/* All candidates */}
      <div className="card">
        <h3 className="font-semibold text-gray-700 mb-3">Other matches</h3>
        <div className="flex flex-col gap-2">
          {result.candidates
            .filter((c) => c.ka !== result.picked_ka)
            .map((c) => (
              <div
                key={c.ka}
                className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <Building2 className="w-5 h-5 text-gray-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{c.title}</p>
                  <p className="text-xs text-gray-500">{c.description}</p>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-center">
        <button onClick={onBack} className="btn-secondary">
          Try Again
        </button>
        <button onClick={onContinue} className="btn-primary flex items-center gap-2">
          Continue <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
