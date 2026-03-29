#!/usr/bin/env node

/**
 * OpenClaw Skill Install Script
 * Deploys alex-law-legal skill to ~/.openclaw/skills/
 */

import fs from 'fs';
import path from 'path';
import os from 'os';

// Configuration
const SKILL_NAME = 'alex_law_legal';
const SKILL_DISPLAY_NAME = 'Alex Law Legal';

// Paths
const scriptDir = path.dirname(new URL(import.meta.url).pathname);
const sourceDir = path.resolve(scriptDir, '..');
const sourceSkillMd = path.join(sourceDir, 'SKILL.md');
const sourceScriptsDir = path.join(sourceDir, 'scripts');

const openclawDir = path.join(os.homedir(), '.openclaw');
const skillsDir = path.join(openclawDir, 'skills');
const targetDir = path.join(skillsDir, SKILL_NAME);
const targetSkillMd = path.join(targetDir, 'SKILL.md');
const targetScriptsDir = path.join(targetDir, 'scripts');
const openclawConfigPath = path.join(openclawDir, 'openclaw.json');

// Utility: Check if path exists
function pathExists(p) {
  try {
    fs.accessSync(p);
    return true;
  } catch {
    return false;
  }
}

// Utility: Recursively copy directory
function copyDirRecursive(src, dest) {
  // Create destination directory
  fs.mkdirSync(dest, { recursive: true });

  // Read source directory
  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// Utility: Check if skill is configured in openclaw.json
function isSkillConfigured() {
  try {
    if (!pathExists(openclawConfigPath)) {
      return false;
    }
    const configContent = fs.readFileSync(openclawConfigPath, 'utf-8');
    const config = JSON.parse(configContent);
    return config?.skills?.entries?.[SKILL_NAME] !== undefined;
  } catch {
    return false;
  }
}

// Main installation logic
function install() {
  console.log(`\n⚖️  ${SKILL_DISPLAY_NAME} - OpenClaw Skill\n`);

  // Check if OpenClaw directory exists
  if (!pathExists(openclawDir)) {
    console.log('⚠️  Warning: ~/.openclaw/ directory not found.');
    console.log('   You may need to install OpenClaw first.\n');
  }

  // Check source files exist
  if (!pathExists(sourceSkillMd)) {
    console.log(`❌ Error: Source SKILL.md not found at ${sourceSkillMd}`);
    process.exit(1);
  }

  if (!pathExists(sourceScriptsDir)) {
    console.log(`❌ Error: Source scripts directory not found at ${sourceScriptsDir}`);
    process.exit(1);
  }

  // Create target directory
  try {
    fs.mkdirSync(targetDir, { recursive: true });
  } catch (err) {
    console.log(`❌ Error: Failed to create target directory: ${err.message}`);
    process.exit(1);
  }

  // Copy SKILL.md
  try {
    fs.copyFileSync(sourceSkillMd, targetSkillMd);
  } catch (err) {
    console.log(`❌ Error: Failed to copy SKILL.md: ${err.message}`);
    process.exit(1);
  }

  // Copy scripts directory
  try {
    copyDirRecursive(sourceScriptsDir, targetScriptsDir);
  } catch (err) {
    console.log(`❌ Error: Failed to copy scripts directory: ${err.message}`);
    process.exit(1);
  }

  // Success message
  console.log(`✅ Installed to ~/.openclaw/skills/${SKILL_NAME}/`);

  // Check configuration
  const isConfigured = isSkillConfigured();

  if (isConfigured) {
    console.log('✅ Configuration found in openclaw.json');
    console.log('\n🚀 Ready! Ask your OpenClaw agent any legal question.\n');
  } else {
    console.log('\n📋 Next steps:');
    console.log('   Add the following to ~/.openclaw/openclaw.json under "skills.entries":\n');
    console.log(`   "${SKILL_NAME}": {`);
    console.log(`     "enabled": true,`);
    console.log(`     "env": {`);
    console.log(`       "ALTA_LEX_USERNAME": "<your_username>",`);
    console.log(`       "ALTA_LEX_PASSWORD": "<your_password>"`);
    console.log(`     }`);
    console.log(`   }\n`);
    console.log('   Then restart your OpenClaw session.\n');
  }
}

// Run installation with error handling
try {
  install();
} catch (err) {
  console.log(`\n❌ Installation failed: ${err.message}\n`);
  process.exit(1);
}
