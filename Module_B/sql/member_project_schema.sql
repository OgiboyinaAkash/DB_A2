-- Module B schema extension for Member Portfolio permissions by shared ProjectID.
-- Run on your local SQL engine if you are keeping member/project data in SQL.

CREATE TABLE IF NOT EXISTS Members (
  member_id INT PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL UNIQUE,
  full_name VARCHAR(255) NOT NULL,
  department VARCHAR(100),
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Projects (
  project_id INT PRIMARY KEY,
  project_name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS MemberProjectMappings (
  mapping_id INT PRIMARY KEY,
  member_id INT NOT NULL,
  project_id INT NOT NULL,
  assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (member_id, project_id),
  FOREIGN KEY (member_id) REFERENCES Members(member_id) ON DELETE CASCADE,
  FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mpm_member_id ON MemberProjectMappings(member_id);
CREATE INDEX IF NOT EXISTS idx_mpm_project_id ON MemberProjectMappings(project_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON Projects(status);
