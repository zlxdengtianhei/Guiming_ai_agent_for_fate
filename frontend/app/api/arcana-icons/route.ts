import { NextResponse } from 'next/server'
import path from 'path'
import { promises as fs } from 'fs'

const ICON_FILES = [
  'cups.svg',
  'pentacles.svg',
  'swords.svg',
  'wands.svg',
  'king.svg',
  'queen.svg',
  'knight.svg',
  'page.svg',
]

export async function GET() {
  try {
    const projectRoot = process.cwd()
    const iconDir = path.resolve(projectRoot, '../database/svg')

    const icons = await Promise.all(
      ICON_FILES.map(async (filename) => {
        const filePath = path.join(iconDir, filename)
        const rawSvg = await fs.readFile(filePath, 'utf-8')
        const svg = rawSvg
          .replace(/#FFFFFF/gi, 'currentColor')
          .replace(/#000000/gi, 'currentColor')

        return {
          name: filename.replace('.svg', ''),
          svg,
        }
      })
    )

    return NextResponse.json({ icons })
  } catch (error) {
    console.error('[arcana-icons] Failed to load SVG icons', error)
    return NextResponse.json({ icons: [] }, { status: 500 })
  }
}


