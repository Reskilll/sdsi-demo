import { NextResponse } from "next/server";

export type ApiSuccess<T = unknown> = {
  success: true;
  data: T;
};

export type ApiError = {
  success: false;
  error: {
    code: string;
    message: string;
  };
};

export type ApiResponse<T = unknown> = ApiSuccess<T> | ApiError;

export function successResponse<T>(data: T, status = 200): NextResponse<ApiSuccess<T>> {
  return NextResponse.json({ success: true, data }, { status });
}

export function errorResponse(
  code: string,
  message: string,
  status: number,
): NextResponse<ApiError> {
  return NextResponse.json({ success: false, error: { code, message } }, { status });
}

export function validationErrorResponse(message: string): NextResponse<ApiError> {
  return errorResponse("VALIDATION_ERROR", message, 400);
}

export function unauthorizedResponse(): NextResponse<ApiError> {
  return errorResponse("UNAUTHORIZED", "Authentication required.", 401);
}

export function forbiddenResponse(): NextResponse<ApiError> {
  return errorResponse("FORBIDDEN", "You do not have permission.", 403);
}

export function notFoundResponse(resource: string): NextResponse<ApiError> {
  return errorResponse("NOT_FOUND", `${resource} not found.`, 404);
}

export function conflictResponse(message: string): NextResponse<ApiError> {
  return errorResponse("CONFLICT", message, 409);
}

export function serverErrorResponse(message = "Internal server error."): NextResponse<ApiError> {
  return errorResponse("SERVER_ERROR", message, 500);
}