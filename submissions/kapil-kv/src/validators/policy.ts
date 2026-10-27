import Joi from "joi";

export const updatePolicySchema = Joi.object({
  targetBusinessHours: Joi.number().min(0.25).required(),
  isActive: Joi.boolean(),
});

export const policyIdParamsSchema = Joi.object({
  id: Joi.string().pattern(/^[a-f\d]{24}$/i).required(),
});