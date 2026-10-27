import Joi from "joi";

export const createGroupSchema = Joi.object({
  name: Joi.string().required().min(1).max(200),
  description: Joi.string().allow("").max(1000).default(""),
  isActive: Joi.boolean().default(true),
});

export const updateGroupSchema = Joi.object({
  name: Joi.string().min(1).max(200),
  description: Joi.string().allow("").max(1000),
  isActive: Joi.boolean(),
});

export const groupIdParamsSchema = Joi.object({
  id: Joi.string().pattern(/^[a-f\d]{24}$/i).required(),
});