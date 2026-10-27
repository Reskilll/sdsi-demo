import { NextRequest, NextResponse } from 'next/server';
import { processExpenses } from '@/lib/engine';
import type { ExpenseInput } from '@/lib/types';

/**
 * POST /api/expenses
 *
 * Accepts a JSON body with { members, expenses } and returns
 * balances, settlements, and validation errors.
 *
 * Rate limiting / size limits:
 *   - Max 50 members
 *   - Max 200 expenses per batch
 *   - Max 10 KB body
 */
const MAX_BODY_SIZE = 10 * 1024; // 10 KB
const MAX_MEMBERS = 50;
const MAX_EXPENSES = 200;

export async function POST(request: NextRequest) {
  try {
    // --- Read body with size check ---
    const contentLength = parseInt(
      request.headers.get('content-length') ?? '0',
      10,
    );

    if (contentLength > MAX_BODY_SIZE) {
      return NextResponse.json(
        { error: 'Request body too large. Max 10 KB.' },
        { status: 413 },
      );
    }

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json(
        { error: 'Invalid JSON in request body.' },
        { status: 400 },
      );
    }

    // --- Structural guard: treat unexpected shapes safely ---
    if (body === null || typeof body !== 'object') {
      return NextResponse.json(
        { error: 'Body must be a JSON object with "members" and "expenses".' },
        { status: 400 },
      );
    }

    const input = body as Record<string, unknown>;

    if (!Array.isArray(input.members) || !Array.isArray(input.expenses)) {
      return NextResponse.json(
        {
          error:
            'Body must contain "members" (array) and "expenses" (array).',
        },
        { status: 400 },
      );
    }

    // --- Resource limits ---
    if (input.members.length > MAX_MEMBERS) {
      return NextResponse.json(
        { error: `Too many members. Maximum is ${MAX_MEMBERS}.` },
        { status: 400 },
      );
    }

    if (input.expenses.length > MAX_EXPENSES) {
      return NextResponse.json(
        { error: `Too many expenses. Maximum is ${MAX_EXPENSES}.` },
        { status: 400 },
      );
    }

    // --- Process ---
    const { result, errors } = processExpenses(input as unknown as ExpenseInput);

    if (errors.length > 0) {
      return NextResponse.json({ errors }, { status: 400 });
    }

    return NextResponse.json(result, { status: 200 });
  } catch (err) {
    // Never leak internal details
    console.error('Unexpected error processing expenses:', err);
    return NextResponse.json(
      { error: 'Internal server error.' },
      { status: 500 },
    );
  }
}

/**
 * GET /api/expenses — return API usage info
 */
export async function GET() {
  return NextResponse.json({
    name: 'Expense Splitter API',
    version: '1.0.0',
    usage: {
      method: 'POST',
      contentType: 'application/json',
      body: {
        members: [{ id: 'string', name: 'string' }],
        expenses: [
          {
            description: 'string',
            total: 'number (> 0)',
            paidBy: 'string (member id)',
            split: {
              type: "'equal' | 'exact' | 'percentage'",
              shareHolderIds: ['string[] (equal)'],
              shares: '{ memberId: number } (exact / percentage)',
            },
            date: 'string? (ISO date)',
          },
        ],
      },
      limits: {
        maxMembers: MAX_MEMBERS,
        maxExpenses: MAX_EXPENSES,
        maxBodySize: `${MAX_BODY_SIZE / 1024} KB`,
      },
    },
  });
}