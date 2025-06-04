import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(
  request: NextRequest,
  { params }: any
): Promise<NextResponse> {
  const filename = params.filename.replace('.json', '');
  
  const { data: image } = await supabase
    .from('uploads')
    .select('*, image_users!inner(oembed_template)')
    .eq('filename', filename)
    .single();

  if (!image) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  let oembed = { ...image.image_users.oembed_template };
  const imageUrl = `https://r.emogir.ls/${image.filename}`;
  
  oembed = JSON.parse(
    JSON.stringify(oembed).replace(/\${url}/g, imageUrl)
      .replace(/\${filename}/g, image.filename)
      .replace(/\${original_name}/g, image.original_name)
  );

  return NextResponse.json(oembed);
} 