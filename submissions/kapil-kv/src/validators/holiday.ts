import Joi from "joi";

export const createHolidaySchema = Joi.object({
  date: Joi.date().iso().required(),
  name: Joi.string().required().min(1).max(200),
  isActive: Joi.boolean().default(true),
});

export const updateHolidaySchema = Joi.object({
  name: Joi.string().min(1).max(200),
  isActive: Joi.boolean(),
});

export const holidayIdParamsSchema = Joi.object({
  id: Joi.string().pattern(/^[a-f\d]{24}$/i).required(),
});