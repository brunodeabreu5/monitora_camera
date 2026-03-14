# Security Guidelines

This document provides security guidelines for the Hikvision Radar Pro V4.2 project.

## Configuration Management

### Runtime Configuration

The application stores runtime configuration in `hikvision_pro_v42_config.json` (located in the application directory). This file contains:

- Camera credentials (IP, username, password)
- Evolution API tokens
- User account information
- Application settings

**⚠️ CRITICAL:** This file is **NOT version controlled** and is listed in `.gitignore`.

### Example Configuration

Use `configs/hikvision_pro_v42_config.example.json` as a template for setting up the configuration:

```bash
cp configs/hikvision_pro_v42_config.example.json hikvision_pro_v42_config.json
# Edit hikvision_pro_v42_config.json with your actual settings
```

## Credentials Management

### Best Practices

1. **Never commit real credentials** to version control
2. **Rotate credentials immediately** if they are accidentally exposed
3. **Use strong passwords** for camera accounts
4. **Rotate API tokens** regularly (Evolution API)
5. **Limit access** to configuration files (file permissions on Linux/Mac)

### Credential Rotation Procedure

If credentials are accidentally committed to git:

1. **Immediately change** all exposed credentials:
   - Camera passwords
   - Evolution API tokens
   - Any API keys or tokens

2. **Remove from git history:**
   ```bash
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch hikvision_pro_v42_config.json'
   git push origin master --force
   ```

3. **Notify collaborators** to re-clone the repository

## Git Security

### Sensitive Files

The following files/folders are excluded from version control (see `.gitignore`):

- `hikvision_pro_v42_config.json` - Runtime configuration
- `*.db` - SQLite database files
- `*.jpg`, `*.jpeg`, `*.png` - Captured images
- `output/` - Output directory with event data
- `__pycache__/`, `*.pyc` - Python cache files
- `build/`, `dist/`, `release/` - Build artifacts

### Pre-commit Hooks (Recommended)

Consider using pre-commit hooks to prevent accidental commits:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: detect-private-key
      - id: detect-aws-credentials
      - id: detect-certificate
```

## Application Security

### Camera Credentials

- **Storage**: Credentials stored in JSON config file (plain text)
- **Access**: Protected by OS file permissions
- **Risk**: Medium - Local file access required
- **Mitigation**: Use strong passwords, limit file access, consider encryption for production

### Evolution API

- **Token Storage**: Stored in JSON config file (plain text)
- **Risk**: Medium - If config file is compromised
- **Mitigation**: Rotate tokens regularly, use dedicated API user with limited permissions

### User Authentication

- **Password Hashing**: SHA-256 with per-user random salt (stored in config as `password_salt`). New passwords and migrated accounts use salted hashes.
- **Legacy accounts**: Users created before salted hashes were introduced are verified with the old unsalted hash; on first successful login they are automatically migrated to a salted hash and the config is saved.
- **Default Credentials**: Admin/Admin (must be changed on first login)
- **Password Policy**: Enforced password change for default accounts

### Network Security

#### Camera Communication

- **Protocol**: HTTP/HTTPS (configurable)
- **Authentication**: HTTP Digest Auth
- **RTSP**: TCP/UDP (configurable transport)

#### Evolution API (WhatsApp Integration)

- **Protocol**: HTTPS
- **Authentication**: Bearer token (API key)
- **Recommendation**: Use HTTPS endpoint, validate SSL certificates

## Data Protection

### Event Data

- **Storage**: SQLite database (`output/events_v42.db`)
- **Content**: Camera events with timestamps, plates, speeds
- **Retention**: Manual (configure database cleanup as needed)

### Images

- **Storage**: `output/images/` directory
- **Format**: JPEG format
- **Retention**: Manual (configure cleanup as needed)

### Logs

- **Location**: `hikvision_pro_v42.log` (application directory)
- **Content**: Runtime errors and informational messages
- **Rotation**: Not automated (configure logrotate if needed)

## Incident Response

### Security Incident Procedure

1. **Identify** the scope of the exposure
2. **Contain** by changing exposed credentials
3. **Notify** affected users/stakeholders
4. **Document** the incident and lessons learned
5. **Review** and update security practices

### Reporting Security Issues

To report security issues:

1. Do NOT open public issues for security vulnerabilities
2. Send details via private communication
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

## Compliance Considerations

### GDPR (General Data Protection Regulation)

If processing EU residents' data:

- **Data Minimization**: Only collect necessary data
- **Purpose Limitation**: Use data only for stated purposes
- **Retention Limits**: Implement data retention policies
- **Subject Rights**: Provide data access/deletion mechanisms
- **Security Measures**: Implement appropriate technical safeguards

### LGPD (Lei Geral de Proteção de Dados - Brazil)

As this application serves Brazilian users, consider LGPD requirements:

- **Data Processing Basis**: Legitimate interest or consent
- **Data Subject Rights**: Access, correction, deletion
- **Security Standards**: Adequate security measures
- **Incident Reporting**: Notify ANPD in case of breaches

## Best Practices Summary

1. ✅ Use strong, unique passwords for all cameras
2. ✅ Rotate API tokens regularly (3-6 months recommended)
3. ✅ Keep software updated (security patches)
4. ✅ Restrict file system access to config files
5. ✅ Use HTTPS for Evolution API when possible
6. ✅ Implement regular database cleanup
7. ✅ Monitor logs for suspicious activity
8. ✅ Never commit credentials to version control
9. ✅ Review `.gitignore` before committing
10. ✅ Use environment-specific configurations

## Version Control Security

### Branch Protection

For production repositories:

- **Protect main/master branch** (require PRs)
- **Enable code reviews** for all changes
- **Use protected branches** for production releases
- **Implement status checks** (CI/CD)

### Access Control

- **Limit write access** to trusted developers
- **Use 2FA** for repository access (GitHub, GitLab, etc.)
- **Review access logs** regularly
- **Revoke access** promptly when team members leave

---

For security questions or concerns, contact the project maintainers.

**Last Updated:** 2026-03-14
