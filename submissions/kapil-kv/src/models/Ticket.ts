import mongoose, { Document, Schema, Model } from "mongoose";
import type { Priority, TicketStatus, StatusEvent } from "@/types";

export interface ITicket extends Document {
  ticketNumber: string;
  title: string;
  description: string;
  priority: Priority;
  status: TicketStatus;
  assigneeGroup: mongoose.Types.ObjectId | null;
  createdAt: Date;
  resolvedAt: Date | null;
  statusHistory: StatusEvent[];
  createdBy: mongoose.Types.ObjectId | null;
  updatedAt: Date;
}

const StatusEventSchema = new Schema<StatusEvent>(
  {
    status: {
      type: String,
      required: true,
      enum: ["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED"],
    },
    timestamp: {
      type: Date,
      required: true,
    },
    reason: {
      type: String,
      trim: true,
      default: "",
    },
  },
  { _id: false },
);

const TicketSchema = new Schema<ITicket>(
  {
    ticketNumber: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    title: {
      type: String,
      required: true,
      trim: true,
    },
    description: {
      type: String,
      trim: true,
      default: "",
    },
    priority: {
      type: String,
      required: true,
      enum: ["P1", "P2", "P3", "P4"],
      index: true,
    },
    status: {
      type: String,
      required: true,
      enum: ["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED"],
      default: "OPEN",
      index: true,
    },
    assigneeGroup: {
      type: Schema.Types.ObjectId,
      ref: "AssigneeGroup",
      default: null,
      index: true,
    },
    resolvedAt: {
      type: Date,
      default: null,
    },
    statusHistory: {
      type: [StatusEventSchema],
      required: true,
      default: [],
    },
    createdBy: {
      type: Schema.Types.ObjectId,
      ref: "Admin",
      default: null,
    },
  },
  {
    timestamps: true,
  },
);

// Compound indexes for common query patterns
TicketSchema.index({ priority: 1, status: 1 });
TicketSchema.index({ status: 1, createdAt: 1 });
TicketSchema.index({ assigneeGroup: 1, status: 1 });
TicketSchema.index({ ticketNumber: "text", title: "text" });

export const Ticket: Model<ITicket> =
  (mongoose.models.Ticket as Model<ITicket>) ||
  mongoose.model<ITicket>("Ticket", TicketSchema);

export default Ticket;