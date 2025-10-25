-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    plan_type VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Transcriptions table
CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT,
    file_size BIGINT,
    language VARCHAR(10) DEFAULT 'en-US',
    transcript_text TEXT,
    srt_content TEXT,
    duration FLOAT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Translations table
CREATE TABLE IF NOT EXISTS translations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    target_language VARCHAR(10) NOT NULL,
    translated_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Voice-overs table
CREATE TABLE IF NOT EXISTS voiceovers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transcription_id UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    voice_type VARCHAR(100) NOT NULL,
    audio_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_project_id ON transcriptions(project_id);
CREATE INDEX IF NOT EXISTS idx_translations_transcription_id ON translations(transcription_id);
CREATE INDEX IF NOT EXISTS idx_voiceovers_transcription_id ON voiceovers(transcription_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE translations ENABLE ROW LEVEL SECURITY;
ALTER TABLE voiceovers ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Users can view their own data" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update their own data" ON users
    FOR UPDATE USING (auth.uid()::text = id::text);

-- RLS Policies for projects table
CREATE POLICY "Users can view their own projects" ON projects
    FOR SELECT USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can create their own projects" ON projects
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update their own projects" ON projects
    FOR UPDATE USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete their own projects" ON projects
    FOR DELETE USING (auth.uid()::text = user_id::text);

-- RLS Policies for transcriptions table
CREATE POLICY "Users can view their own transcriptions" ON transcriptions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = transcriptions.project_id
            AND projects.user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Users can create transcriptions in their projects" ON transcriptions
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = transcriptions.project_id
            AND projects.user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Users can update their own transcriptions" ON transcriptions
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = transcriptions.project_id
            AND projects.user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Users can delete their own transcriptions" ON transcriptions
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM projects
            WHERE projects.id = transcriptions.project_id
            AND projects.user_id::text = auth.uid()::text
        )
    );
