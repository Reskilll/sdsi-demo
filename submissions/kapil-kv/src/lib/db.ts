import mongoose from "mongoose";
import { getEnv } from "./env";

const globalForMongoose = globalThis as unknown as {
  _mongooseCache: {
    conn: typeof mongoose | null;
    promise: Promise<typeof mongoose> | null;
  };
};

if (!globalForMongoose._mongooseCache) {
  globalForMongoose._mongooseCache = { conn: null, promise: null };
}

export async function connectDB(): Promise<typeof mongoose> {
  const cache = globalForMongoose._mongooseCache;

  if (cache.conn) {
    return cache.conn;
  }

  if (!cache.promise) {
    const env = getEnv();
    const uri = env.MONGODB_URI;

    cache.promise = mongoose.connect(uri, {
      bufferCommands: false,
      maxPoolSize: 10,
    });
  }

  try {
    cache.conn = await cache.promise;
  } catch (e) {
    cache.promise = null;
    throw e;
  }

  return cache.conn;
}

export function getMongooseInstance(): typeof mongoose {
  return mongoose;
}