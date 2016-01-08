

def bbox_filter(table, bbox):
    '''Table is actual table object, bbox is of the form
    [lon1, lat1, lon2, lat2]

    Returns rows as a list

    '''
    # TODO: Make this faster
    # Generate the polygon for the bounding box
    coords = [[bbox[0], bbox[1]], [bbox[0], bbox[3]], [bbox[2], bbox[3]],
              [bbox[2], bbox[1]], [bbox[0], bbox[1]]]
    coords_str = [[str(number) for number in coord] for coord in coords]
    coord_text = ', '.join([' '.join(coord) for coord in coords_str])
    box = 'POLYGON(({}))'.format(coord_text)

    filtered = table.select().where(table.c.geom.intersects(box))

    return filtered
