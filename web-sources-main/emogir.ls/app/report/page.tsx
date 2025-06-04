"use client";

import { Header } from "@/components/ui/header";
import { Footer } from "@/components/ui/footer";
import { motion } from "framer-motion";
import { useState, Suspense } from "react";
import { Button } from "@/components/ui/button";
import { useSearchParams } from "next/navigation";

type ReportType = "profile" | "image";

function ReportForm() {
  const searchParams = useSearchParams();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const initialType = (searchParams.get("type") as ReportType) || "profile";
  const initialTarget =
    searchParams.get("link") || searchParams.get("username") || "";

  const [formData, setFormData] = useState({
    type: initialType,
    targetId: initialTarget,
    reason: "",
    details: "",
    email: "",
  });

  const reasons = {
    profile: [
      "Inappropriate content",
      "Impersonation",
      "Spam",
      "Harassment",
      "Other",
    ],
    image: [
      "Explicit content",
      "Copyright violation",
      "Harmful content",
      "Misleading content",
      "Other",
    ],
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error("Failed to submit report");
      }

      setSubmitted(true);
    } catch (error) {
      console.error("Error submitting report:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <span className="inline-block px-4 py-1.5 text-xs font-medium text-primary border border-primary/30 rounded-full mb-4">
          Report Content
        </span>
      </motion.div>

      <motion.h1
        className="text-3xl font-bold mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        Submit a Report
      </motion.h1>

      {submitted ? (
        <motion.div
          className="bg-primary/10 border border-primary/30 rounded-lg p-6 text-center"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="text-xl font-semibold mb-2">Thank You</h2>
          <p className="text-white/70">
            Your report has been submitted and will be reviewed by our team.
          </p>
        </motion.div>
      ) : (
        <motion.form
          onSubmit={handleSubmit}
          className="space-y-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div>
            <label className="block text-sm font-medium mb-2">
              Report Type
            </label>
            <select
              value={formData.type}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  type: e.target.value as ReportType,
                })
              }
              className="w-full bg-darker border border-primary/30 rounded-lg p-3 text-white/90"
              required
            >
              <option value="profile">Profile</option>
              <option value="image">Image</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              {formData.type === "profile" ? "Username" : "Image URL"}
            </label>
            <input
              type="text"
              value={formData.targetId}
              onChange={(e) =>
                setFormData({ ...formData, targetId: e.target.value })
              }
              className="w-full bg-darker border border-primary/30 rounded-lg p-3 text-white/90"
              placeholder={
                formData.type === "profile"
                  ? "Enter username"
                  : "Enter image URL"
              }
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Reason</label>
            <select
              value={formData.reason}
              onChange={(e) =>
                setFormData({ ...formData, reason: e.target.value })
              }
              className="w-full bg-darker border border-primary/30 rounded-lg p-3 text-white/90"
              required
            >
              <option value="">Select a reason</option>
              {reasons[formData.type].map((reason) => (
                <option key={reason} value={reason}>
                  {reason}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Additional Details
            </label>
            <textarea
              value={formData.details}
              onChange={(e) =>
                setFormData({ ...formData, details: e.target.value })
              }
              className="w-full bg-darker border border-primary/30 rounded-lg p-3 text-white/90 min-h-[100px]"
              placeholder="Please provide any additional information"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Your Email (optional)
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
              className="w-full bg-darker border border-primary/30 rounded-lg p-3 text-white/90"
              placeholder="Enter your email for updates"
            />
          </div>

          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Submitting..." : "Submit Report"}
          </Button>
        </motion.form>
      )}
    </div>
  );
}

export default function ReportPage() {
  return (
    <>
      <div className="fixed inset-0 -z-10 animated-bg" />
      <main className="mx-auto h-full w-full max-w-[1200px] px-[45px] py-0 relative overflow-hidden">
        <Header />
        <section className="relative mt-[40px] mb-[150px] py-10">
          <Suspense fallback={<div>Loading...</div>}>
            <ReportForm />
          </Suspense>
        </section>
      </main>
      <Footer />
    </>
  );
}
