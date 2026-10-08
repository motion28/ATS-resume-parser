export type Experience = {
  company: string | null
  title: string | null
  start_date: string | null
  end_date: string | null
  description: string | null
}

export type Education = {
  institution: string | null
  degree: string | null
  field_of_study: string | null
  graduation_date: string | null
}

export type ParsedResume = {
  name: string | null
  email: string | null
  phone: string | null
  location: string | null
  skills: string[]
  experience: Experience[]
  education: Education[]
}

export type ParseResult = {
  filename: string
  text: string
  resume: ParsedResume
}

function hasNullableStrings(value: unknown, fields: string[]): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && fields.every((field) => {
    const item = (value as Record<string, unknown>)[field]
    return item === null || typeof item === 'string'
  })
}

// TypeScript types alone do not validate JSON received over HTTP.
export function isParseResult(value: unknown): value is ParseResult {
  if (typeof value !== 'object' || value === null) return false
  const data = value as Record<string, unknown>
  const resume = data.resume
  return typeof data.filename === 'string' && typeof data.text === 'string'
    && hasNullableStrings(resume, ['name', 'email', 'phone', 'location'])
    && Array.isArray(resume.skills) && resume.skills.every((skill) => typeof skill === 'string')
    && Array.isArray(resume.experience) && resume.experience.every((item) =>
      hasNullableStrings(item, ['company', 'title', 'start_date', 'end_date', 'description']))
    && Array.isArray(resume.education) && resume.education.every((item) =>
      hasNullableStrings(item, ['institution', 'degree', 'field_of_study', 'graduation_date']))
}
