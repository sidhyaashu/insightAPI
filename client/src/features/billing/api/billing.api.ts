import apiClient from "@/lib/api-client";
import type { Subscription } from "@/lib/api-client/types";
import { getMockUser } from "@/lib/api-client/mockFallback";

export const billingApi = {
  getSubscription: async (): Promise<Subscription> => {
    try {
      const { data } = await apiClient.get<Subscription>("/payments/subscription");
      return data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        const user = getMockUser();
        return {
          tier: user.tier,
          status: user.tier === "FREE" ? "free" : "active",
          current_period_end: new Date(Date.now() + 30 * 86400000).toISOString(),
          cancel_at_period_end: false,
          subscription: null,
        };
      }
      throw err;
    }
  },

  createCheckoutSession: async (priceId: string): Promise<{ checkout_url: string }> => {
    try {
      const { data } = await apiClient.post<{ checkout_url: string }>("/payments/checkout", { price_id: priceId });
      return data;
    } catch (err: any) {
      if (!err.response || err.code === "ERR_NETWORK" || err.message?.includes("Network Error")) {
        return { checkout_url: "/billing?session=mock_success" };
      }
      throw err;
    }
  },
};
