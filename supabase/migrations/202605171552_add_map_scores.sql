create table if not exists public.map_scores (
  matchid integer primary key,
  team1_name text not null,
  team2_name text not null,
  team1_score integer not null default 0 check (team1_score >= 0 and team1_score <= 99),
  team2_score integer not null default 0 check (team2_score >= 0 and team2_score <= 99),
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);
