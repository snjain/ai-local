
import { createClient } from '@supabase/supabase-js';
import { Database } from '../types/database.types';

// Get environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Check if environment variables are defined
if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing required environment variables: VITE_SUPABASE_URL and/or VITE_SUPABASE_ANON_KEY. ' +
    'Please ensure your root .env file includes these variables (see .env.example for reference).'
  );
}

// Initialize Supabase client
export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey);

export type SupabaseClient = typeof supabase;
