import mongoose, { Document, Schema, Model } from "mongoose";

export interface IHoliday extends Document {
  date: Date;
  name: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

const HolidaySchema = new Schema<IHoliday>(
  {
    date: {
      type: Date,
      required: true,
      unique: true,
      index: true,
    },
    name: {
      type: String,
      required: true,
      trim: true,
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

export const Holiday: Model<IHoliday> =
  (mongoose.models.Holiday as Model<IHoliday>) ||
  mongoose.model<IHoliday>("Holiday", HolidaySchema);

export default Holiday;