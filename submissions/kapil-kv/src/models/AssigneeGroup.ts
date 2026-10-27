import mongoose, { Document, Schema, Model } from "mongoose";

export interface IAssigneeGroup extends Document {
  name: string;
  description?: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

const AssigneeGroupSchema = new Schema<IAssigneeGroup>(
  {
    name: {
      type: String,
      required: true,
      unique: true,
      trim: true,
      index: true,
    },
    description: {
      type: String,
      trim: true,
      default: "",
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

export const AssigneeGroup: Model<IAssigneeGroup> =
  (mongoose.models.AssigneeGroup as Model<IAssigneeGroup>) ||
  mongoose.model<IAssigneeGroup>("AssigneeGroup", AssigneeGroupSchema);

export default AssigneeGroup;