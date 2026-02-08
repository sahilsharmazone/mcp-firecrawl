"use client";

import { useState, useEffect } from "react";

interface Vehicle {
  id: number;
  title: string;
  vin: string;
  price: number;
  mileage: number;
  year: number;
  fuel_type: string;
  transmission: string;
  listing_url: string;
  website_url: string;
  exterior_color: string;
  engine: string;
  trim: string;
  scraped_at: string;
}

interface Prediction {
  vehicle_id: number;
  predicted_price: number;
  actual_price: number;
  difference: number;
}

export default function Home() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [predictions, setPredictions] = useState<{ [key: number]: Prediction }>({});

  const API_URL = "http://localhost:8000";

  useEffect(() => {
    fetchVehicles();
  }, []);

  const fetchVehicles = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/vehicles`);
      if (res.ok) {
        const data = await res.json();
        setVehicles(data);
      } else {
        console.error("Failed to fetch vehicles");
      }
    } catch (error) {
      console.error("Error fetching vehicles:", error);
    } finally {
      setLoading(false);
    }
  };

  const handlePredict = async (id: number) => {
    try {
      const res = await fetch(`${API_URL}/vehicles/${id}/predict`);
      if (res.ok) {
        const data = await res.json();
        setPredictions((prev) => ({ ...prev, [id]: data }));
      } else {
        console.error("Prediction failed");
        alert("Prediction failed. Ensure API is running and model is trained.");
      }
    } catch (error) {
      console.error("Error predicting:", error);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await fetch(`${API_URL}/trigger-sync`, { method: "POST" });
      if (res.ok) {
        alert("Sync triggered! Check API logs.");
      } else {
        alert("Sync failed to trigger.");
      }
    } catch (error) {
      console.error("Error triggering sync:", error);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              Audi Inventory Dashboard
            </h1>
            <p className="text-gray-400 mt-2">
              Real-time scraping & AI Price Prediction
            </p>
          </div>
          <button
            onClick={handleSync}
            disabled={syncing}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${syncing
              ? "bg-gray-700 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-500 shadow-lg hover:shadow-blue-500/25"
              }`}
          >
            {syncing ? "Syncing..." : "Sync Now"}
          </button>
        </header>

        {loading ? (
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading inventory...</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-800 shadow-2xl bg-gray-900/50 backdrop-blur-sm">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-800 text-gray-400 uppercase text-xs">
                <tr>
                  <th className="px-6 py-4">Vehicle</th>
                  <th className="px-6 py-4">Specs</th>
                  <th className="px-6 py-4">Price</th>
                  <th className="px-6 py-4">AI Prediction</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {vehicles.map((v) => {
                  const prediction = predictions[v.id];
                  return (
                    <tr key={v.id} className="hover:bg-gray-800/50 transition-colors">
                      <td className="px-6 py-4 font-medium text-white max-w-xs truncate">
                        {v.title}
                        <div className="text-xs text-gray-500 mt-1">{v.vin}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col gap-1">
                          <span className="badge bg-gray-800 px-2 py-0.5 rounded text-xs w-fit">
                            {v.year}
                          </span>
                          <span>{v.mileage?.toLocaleString()} km</span>
                          <span className="text-gray-500 text-xs">{v.trim}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-emerald-400 font-bold text-lg">
                        ${v.price?.toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        {prediction ? (
                          <div className="flex flex-col">
                            <span className="text-blue-400 font-bold text-lg">
                              ${prediction.predicted_price.toLocaleString()}
                            </span>
                            <span
                              className={`text-xs ${prediction.difference > 0
                                ? "text-red-400"
                                : "text-green-400"
                                }`}
                            >
                              {prediction.difference > 0 ? "+" : ""}
                              ${prediction.difference.toLocaleString()} vs Actual
                            </span>
                          </div>
                        ) : (
                          <span className="text-gray-600 italic">No prediction</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handlePredict(v.id)}
                          className="text-blue-400 hover:text-blue-300 text-sm font-semibold border border-blue-400/30 hover:bg-blue-400/10 px-3 py-1.5 rounded-md transition-all"
                        >
                          Predict Price
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
