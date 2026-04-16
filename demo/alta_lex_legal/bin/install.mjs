#!/usr/bin/env node

/**
 * OpenClaw Skill Install Script
 * Deploys alta_lex_legal skill to ~/.openclaw/skills/
 */

import fs from 'fs';
import path from 'path';
import os from 'os';

const SKILL_NAME = 'alta_lex_legal';
const SKILL_DISPLAY_NAME = 'Alta Lex Legal AI';

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

function pathExists(p) {
  try { fs.accessSync(p); return true; } catch { return false; }
}

function copyDirRecursive(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.name === '__pycache__' || entry.name.endsWith('.pyc')) continue;
    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function isSkillConfigured() {
  try {
    if (!pathExists(openclawConfigPath)) return false;
    const config = JSON.parse(fs.readFileSync(openclawConfigPath, 'utf-8'));
    return config?.skills?.entries?.[SKILL_NAME] !== undefined;
  } catch { return false; }
}

function install() {
  console.log(`\n  ${SKILL_DISPLAY_NAME} - OpenClaw Skill Installer\n`);

  if (!pathExists(openclawDir)) {
    console.log('  Warning: ~/.openclaw/ directory not found.');
    console.log('  You may need to install OpenClaw first.\n');
  }

  if (!pathExists(sourceSkillMd)) {
    console.log(`  Error: Source SKILL.md not found at ${sourceSkillMd}`);
    process.exit(1);
  }
  if (!pathExists(sourceScriptsDir)) {
    console.log(`  Error: Source scripts directory not found at ${sourceScriptsDir}`);
    process.exit(1);
  }

  // Create target and copy files
  try {
    fs.mkdirSync(targetDir, { recursive: true });
    fs.copyFileSync(sourceSkillMd, targetSkillMd);
    copyDirRecursive(sourceScriptsDir, targetScriptsDir);
  } catch (err) {
    console.log(`  Error: Installation failed: ${err.message}`);
    process.exit(1);
  }

  console.log(`  Installed to ~/.openclaw/skills/${SKILL_NAME}/`);
  console.log(`  Files copied: SKILL.md + scripts/ (11 modules)\n`);

  if (isSkillConfigured()) {
    console.log('  Configuration found in openclaw.json');
    console.log('\n  Ready! Ask your OpenClaw agent any legal question.\n');
  } else {
    console.log('  Next steps:');
    console.log('  Add the following to ~/.openclaw/openclaw.json under "skills.entries":\n');
    console.log(`  "${SKILL_NAME}": {`);
    console.log(`    "enabled": true,`);
    console.log(`    "env": {`);
    console.log(`      "ALTA_LEX_USERNAME": "<your_username>",`);
    console.log(`      "ALTA_LEX_PASSWORD": "<your_password>"`);
    console.log(`    }`);
    console.log(`  }\n`);
    console.log('  Then restart your OpenClaw session.\n');
  }
}

try { install(); } catch (err) {
  console.log(`\n  Installation failed: ${err.message}\n`);
  process.exit(1);
}
