import mongoose, { Document, Schema, Model } from "mongoose";
import type { Priority } from "@/types";

export interface ISLAPolicy extends Document {
  priority: Priority;
  targetBusinessHours: number;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

const SLAPolicySchema = new Schema<ISLAPolicy>(
  {
    priority: {
      type: String,
      required: true,
      unique: true,
      enum: ["P1", "P2", "P3", "P4"],
      index: true,
    },
    targetBusinessHours: {
      type: Number,
      required: true,
      min: 0.25, // Minimum 15 minutes
    },
    isActive: {
      type: Boolean,
      default: true,
    },
  },
  {
    timestamps: true,
  },
);

export const SLAPolicy: Model<ISLAPolicy> =
  (mongoose.models.SLAPolicy as Model<ISLAPolicy>) ||
  mongoose.model<ISLAPolicy>("SLAPolicy", SLAPolicySchema);

export default SLAPolicy;