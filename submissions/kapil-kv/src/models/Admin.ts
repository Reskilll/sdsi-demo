import mongoose, { Document, Schema, Model } from "mongoose";
import bcrypt from "bcryptjs";

export interface IAdmin extends Document {
  email: string;
  passwordHash: string;
  role: string;
  createdAt: Date;
  updatedAt: Date;
}

const AdminSchema = new Schema<IAdmin>(
  {
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
      index: true,
    },
    passwordHash: {
      type: String,
      required: true,
      select: false, // Never returned by default
    },
    role: {
      type: String,
      required: true,
      default: "ADMIN",
      enum: ["ADMIN"],
    },
  },
  {
    timestamps: true,
  },
);

// Instance method to compare passwords
AdminSchema.methods.comparePassword = async function (
  candidatePassword: string,
): Promise<boolean> {
  const doc = await (this.constructor as Model<IAdmin>)
    .findById(this._id)
    .select("+passwordHash")
    .exec();

  if (!doc) return false;
  return bcrypt.compare(candidatePassword, doc.passwordHash);
};

// Static method to hash a password
AdminSchema.statics.hashPassword = async function (password: string): Promise<string> {
  const salt = await bcrypt.genSalt(12);
  return bcrypt.hash(password, salt);
};

export interface IAdminMethods {
  comparePassword(candidatePassword: string): Promise<boolean>;
}

export interface IAdminStatics {
  hashPassword(password: string): Promise<string>;
}

export const Admin: Model<IAdmin, Record<string, never>, IAdminMethods> & IAdminStatics =
  (mongoose.models.Admin as any) ||
  mongoose.model<IAdmin, Model<IAdmin, Record<string, never>, IAdminMethods> & IAdminStatics>(
    "Admin",
    AdminSchema,
  );

export default Admin;