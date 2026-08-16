/**
 * Application-wide constants.
 *
 * Values that differ per environment come from Vite env variables so that
 * nothing environment-specific is hard-coded in components.
 */

export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Letter Registry System'
export const APP_SHORT_NAME = 'LRS'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const PRODUCTION_CREDIT = 'A Production of AJ-Labs'
