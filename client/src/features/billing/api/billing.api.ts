import apiClient from "@/lib/api-client";
import type { Subscription } from "@/lib/api-client/types";

export const billingApi = {
  getSubscription: async (): Promise<Subscription> => {
    const { data } = await apiClient.get<Subscription>("/payments/subscription");
    return data;
  },

  getPlans: async (): Promise<Record<string, string>> => {
    const { data } = await apiClient.get<Record<string, string>>("/payments/plans");
    return data;
  },

  createCheckoutSession: async (priceId: string): Promise<{ checkout_url: string }> => {
    const { data } = await apiClient.post<{ checkout_url: string }>("/payments/checkout", { price_id: priceId });
    return data;
  },

  createPortalSession: async (): Promise<{ portal_url: string }> => {
    const { data } = await apiClient.post<{ portal_url: string }>("/payments/portal");
    return data;
  },

  updateOveragePreference: async (allowOverage: boolean): Promise<{ allow_overage: boolean; message: string }> => {
    const { data } = await apiClient.patch<{ allow_overage: boolean; message: string }>("/users/me/preferences", {
      allow_overage: allowOverage,
    });
    return data;
  },
};

